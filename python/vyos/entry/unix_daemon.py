import os
import sys
import socket
import argparse


class Terminated(BaseException):
    pass


def nop(*args):
    pass


def daemon(unix_socket, callback):
    # Make sure the socket does not already exist
    try:
        os.unlink(unix_socket)
    except OSError:
        if os.path.exists(unix_socket):
            raise

    # Create a UDS socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the address
    print('starting up on {}'.format(unix_socket))
    sock.bind(unix_socket)

    # Listen for incoming connection, backlog up to 64
    # 64..0k ought to be enough for anybody, says the rumour
    sock.listen(64)

    while True:
        # Wait for a connection
        connection, _ = sock.accept()
        try:
            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(1024)
                if not data:
                    break
                callback(connection, data)
        except Terminated:
            pass
        finally:
            # Clean up the connection
            connection.close()


def validator():
    from vyos.entry.validator import main as validate

    def exit(query, connection):
        def _answer(response):
            # print(query.strip())
            # print(response.decode('utf-8').strip())
            connection.sendall(response)

        def _exit(exiting=None, *args):
            if exiting is None:
                _answer(b'0\n')

            elif isinstance(exiting, int):
                _answer(bytes(f'{exiting}\n', 'ascii'))

            elif isinstance(exiting, str):
                answer = bytes(exiting.strip().replace('\n', '\\n') + '\n')
                _answer(answer)
                connection.sendall('1\n')

            else:
                _answer(b'1\n')

            sys.exit = nop
            raise Terminated()

        return _exit

    def callback(connection, data):
        sys.argv = ['validators'] + [_.decode() for _ in data.split()]
        sys.exit = exit('validator {}'.format(data.decode('utf-8')), connection)
        validate()

    daemon('validator.socket', callback)
    # daemon('/run/validator.socket', callback)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--validator", action="store_true", help="start the validator daemon")
    args = parser.parse_args()

    if args.validator:
        validator()

    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
