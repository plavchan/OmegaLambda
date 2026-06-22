import socket
import logging

class TheSkyXSocketWrapper:
    """
    A lightweight TCP socket wrapper that mimics a subset of the legacy 
    COM object functionality by translating properties into TheSkyX JavaScript.
    """
    def __init__(self, host="127.0.0.1", port=3040):
        self.host = host
        self.port = port

    def send_js(self, script):
        """
        Formats and sends a JavaScript string payload directly over the network 
        to TheSkyX cross-platform TCP engine server on port 3040.
        """
        # Software Bisque's TCP engine strictly mandates this syntax prefix
        payload = f"/* Java Script */\n/* Socket Start Packet */\n{script}\n/* Socket End Packet */"
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)
                s.connect((self.host, self.port))
                s.sendall(payload.encode('utf-8'))
                
                # Retrieve returned telemetry packet string
                response = s.recv(1024).decode('utf-8')
                
                # TheSkyX appends '|No error.' to successful evaluations.
                # Clean up the output string to isolate the actual return values.
                if '|' in response:
                    return response.split('|')[0].strip()
                return response.strip()
        except Exception as e:
            logging.error(f"TheSkyX TCP Server communication failed: {e}")
            return "-100"