import socket

def main():
    HOST = '127.0.0.1'
    PORT = 8080
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f'Listening on {HOST}:{PORT} for Movesense data...')
        conn, addr = s.accept()
        with conn:
            print(f'Connected by {addr}')
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(data.decode('utf-8', errors='replace'), end='')

if __name__ == '__main__':
    main()
