import socket
import sys


server_addr = ('127.0.0.1',5000)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(server_addr)

sys.stdout.write(client.recv(1024))
sys.stdout.write('>>')

data_port = 0
nama_file = ''
i = 0
try:
	while True:
		#print i
		msg = sys.stdin.readline()
		if " " in msg:
			nama_file = msg.split(' ',1)[1][:-1]
			#print nama_file
		if i==0:
			if "USER" not in msg:
				client.send("USER anonymous")
				pesan = client.recv(1024)
				sys.stdout.write(pesan)
				if "331" in pesan:
					client.send("PASS ****")
					pesan = client.recv(1024)
					sys.stdout.write(pesan)
					print "Could't to connect server"
			else:
				client.send(msg)
				pesan = client.recv(1024)
				sys.stdout.write(pesan)
		else:
			client.send(msg)
			pesan = client.recv(1024)
			sys.stdout.write(pesan)
		if "221" in pesan:
			#sys.stdout.write(pesan)
			client.close()
			sys.exit(0)
			break
		if "530" in pesan:
			#sys.stdout.write(pesan)
			client.close()
			sys.exit(0)
		if "Entering Passive Mode" in pesan:
			lala=''
			p1 = int(pesan.split(',')[4])
			p2 = int(pesan.split(',')[5].split(')')[0])
			data_port = p1 * 256 + p2
		if "LIST" in msg:
			data=''
			client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client1.connect(('127.0.1.1',data_port))
			data = client1.recv(1024)
			#sys.stdout.write(data)
			while data:
				tmp=client1.recv(1024)
				if tmp=='':
					break
				data=data+tmp
			sys.stdout.write(data)
			pesan = client.recv(1024)
			print pesan
			client1.close()
		if "RETR" in msg:
			client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client1.connect(('127.0.1.1',data_port))
			with open (nama_file, 'wb') as f:
				data = ""
				while True:
					data = client1.recv(1024)
					if not data:break
					f.write(data)
			f.close()
			pesan = client.recv(1024)
			print pesan
			client1.close()
		if "STOR" in msg:
			client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client1.connect(('127.0.1.1',data_port))
			with open (nama_file, 'rb') as f:
				data = ""
				data = f.read(1024)
				while data:
					client1.send(data)
					data = f.read(1024)
			f.close()
			#pesan = client.recv(1024)
			#print pesan
			client1.close()
		sys.stdout.write('>>')
		i+=1

except KeyboardInterrupt:
	client.close()

	sys.exit(0)

