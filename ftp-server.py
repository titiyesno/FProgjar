import socket
import select
import threading
import os 
import sys
import time

allow_delete = False
local_ip = socket.gethostbyname(socket.gethostname())
currdir = os.path.abspath('.')

class ftpserver(threading.Thread):
	def __init__(self):
		self.host = '127.0.0.1'
		self.port = 5000
		self.mode = 'I'
		self.backlog = 5
		self.size = 1024
		self.threads = []
		threading.Thread.__init__(self)

	def open_socket(self):
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
		self.server.bind((self.host, self.port))
		self.server.listen(5)

	def run(self):
		self.open_socket()
		input = [self.server, sys.stdin]
		running = 1
		while running:
			inputready, outputready, exceptready = select.select(input, [], [])

			for s in inputready:
				if s == self.server:
					print s
					c = ftpserverfunc(self.server.accept())
					c.start()
					self.threads.append(c)
				elif s == sys.stdin:
					junk = sys.stdin.readline()
					running = 0

		self.server.close()
		for c in self.threads:
			c.join()

class ftpserverfunc(threading.Thread):
	def __init__(self, (client,address)):
		threading.Thread.__init__(self)
		self.client = client
		self.address = address
		self.basewd = currdir
		self.cwd = self.basewd
		self.rest = False
		self.pasv_mode = False
		self.size = 1024
		self.running = True

	def run(self):
		self.client.send('220 Welcome!\r\n')
		while self.running:
			cmd = self.client.recv(self.size)
			if not cmd:
				break
			else:
				print 'recv: ',cmd
				try:
					func=getattr(self, cmd[:4].strip().upper())
					func(cmd)
				except Exception,e:
					print e
					self.client.send('500 Sorry.\r\n')

	def USER(self,cmd):
		global flag
		flag = 0
		if cmd.strip().split()[1]==str(sys.argv[1]):
			self.client.send('331 Please specify the password.\r\n')
		else:
			self.client.send('331 Please specify the password.\r\n')
			flag = 1

	def PASS(self,cmd):
		if flag == 1:
			self.client.send('530 Login incorrect\r\n')
			self.running = False
			self.client.close()
		elif cmd.strip().split()[1]==str(sys.argv[2]):
			self.client.send('230 User logged in, proceed.\r\n')
		else:
			self.client.send('530 Login incorrect\r\n')
			#exit()
			self.running = False
			self.client.close()

	def PWD(self,cmd):
		cwd=os.path.relpath(self.cwd,self.basewd)
		if cwd=='.':
			cwd='/'
		else:
			cwd='/'+cwd
		print cwd
		self.client.send('257 \"%s\"\r\n' % cwd)

	def CWD(self,cmd):
		chwd=cmd[4:-1]
		if chwd=='/':
			self.cwd=self.basewd
		elif chwd[0]=='/':
			self.cwd=os.path.join(self.basewd,chwd[1:])
		else:
			self.cwd=os.path.join(self.cwd,chwd)
		self.client.send('250 Working directory changed.\r\n')

	def QUIT(self,cmd):
		self.client.send('221 Goodbye.\r\n')
		self.running = False
		self.client.close()

	#Mengganti nama file (RNTO: 4.1.3)
	def RNTO(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-1])
		os.rename(self.rnfn,fn)
		self.client.send('250 File renamed.\r\n')

	def RNFR(self,cmd):
		self.rnfn=os.path.join(self.cwd,cmd[5:-1])
		self.client.send('350 Ready.\r\n')

	#Membuat direktori (MKD: 4.1.3)
	def MKD(self,cmd):
		dn=os.path.join(self.cwd,cmd[4:-1])
		os.mkdir(dn)
		self.client.send('257 Directory created.\r\n')

	#Mendaftar file dan direktori (LIST: 4.1.3)
	def LIST(self,cmd):
		self.client.send('150 Here comes the directory listing.\r\n')
		print 'list:', self.cwd
		self.start_datasock()
		for t in os.listdir(self.cwd):
			k=self.toListItem(os.path.join(self.cwd,t))
			self.datasock.send(k+'\r\n')
		self.stop_datasock()
		self.client.send('226 Directory send OK.\r\n')

	def TYPE(self,cmd):
		self.mode=cmd[5]
		self.client.send('200 Binary mode.\r\n')

	def toListItem(self,fn):
		st=os.stat(fn)
		fullmode='rwxrwxrwx'
		mode=''
		for i in range(9):
			mode+=((st.st_mode>>(8-i))&1) and fullmode[i] or '-'
		d=(os.path.isdir(fn)) and 'd' or '-'
		ftime=time.strftime(' %b %d %H:%M ',time.gmtime(st.st_mtime))
		return d+mode+' 1 user group '+str(st.st_size)+ftime+os.path.basename(fn)

	def PASV(self,cmd):
		self.pasv_mode = True
		self.servsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.servsock.bind((local_ip,0))
		self.servsock.listen(1)
		#ip = '127.0.0.1'
		#port = 5000
		ip, port = self.servsock.getsockname()
		print 'open', ip, port
		self.client.send('227 Entering Passive Mode (%s,%u,%u).\r\n' %
				(','.join(ip.split('.')), port>>8&0xFF, port&0xFF))

	def PORT(self,cmd):
		if self.pasv_mode:
			self.servsock.close()
			self.pasv_mode = False
		l=cmd[5:].split(',')
		self.dataAddr='.'.join(l[:4])
		self.dataPort=(int(l[4])<<8)+int(l[5])
		self.client.send('200 Get port.\r\n')

	def start_datasock(self):
		if self.pasv_mode:
			self.datasock, addr = self.servsock.accept()
			print 'connect:', addr
		else:
			self.datasock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.datasock.connect((self.dataAddr,self.dataPort))

	def stop_datasock(self):
		self.datasock.close()
		if self.pasv_mode:
			self.servsock.close()

	# HELP: 4.1.3
	def HELP(self,cmd):
		self.client.send('214-The following commands are recognized:\r\nCWD\r\nQUIT\r\nRETR\r\nSTOR\r\nRNTO\r\nDELE\r\nRMD\r\nMKD\r\nPWD\r\nLIST\r\nHELP\r\nPASV\r\n')

	# Download file

	def RETR(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-1])
		print 'Downlowding:',fn
		if self.mode=='I':
			fi=open(fn,'rb')
		else:
			fi=open(fn,'r')
		self.client.send('150 Opening data connection.\r\n')
		if self.rest:
			fi.seek(self.pos)
			self.rest=False
		data= fi.read(1024)
		self.start_datasock()
		while data:
			self.datasock.send(data)
			data=fi.read(1024)
		fi.close()
		self.stop_datasock()
		self.client.send('226 Transfer complete.\r\n')

	def STOR(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-1])
		print 'Uploading:',fn
		if self.mode=='I':
			fo=open(fn,'wb')
		else:
			fo=open(fn,'w')
		self.client.send('150 Opening data connection.\r\n226 Transfer complete.\r\n')
		self.start_datasock()
		while True:
			data=self.datasock.recv(1024)
			if not data: break
			fo.write(data)
		fo.close()
		self.stop_datasock()
		#self.conn.send('226 Transfer complete.\r\n')

	def DELE(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-1])
		allow_delete = True
		if allow_delete:
			os.remove(fn)
			self.client.send('250 File deleted.\r\n')
			allow_delete = False
		else:
			self.client.send('450 Not allowed.\r\n')

	def RMD(self,cmd):
		dn=os.path.join(self.cwd,cmd[4:-1])
		allow_delete = True
		if allow_delete:
			os.rmdir(dn)
			self.client.send('250 Directory deleted.\r\n')
			allow_delete = False
		else:
			self.client.send('450 Not allowed.\r\n')

if __name__=='__main__':
	ftp = ftpserver()
	ftp.daemon = True
	ftp.start()
	raw_input('Enter to end...\n')
	#ftp.stop()
