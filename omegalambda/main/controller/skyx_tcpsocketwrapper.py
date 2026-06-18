import socket

class TheSky64SocketWrapper:
    def __init__(self, host="127.0.0.1", port=3040):
        self.host = host
        self.port = port

    def send_js(self, script):
        """Sends JavaScript directly to TheSky64 TCP server and grabs the output."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.host, self.port))
                s.sendall(script.encode('utf-8'))
                response = s.recv(1024).decode('utf-8')
                # TheSky appends '|No error.' to successful responses
                return response.split('|')[0].strip()
        except Exception as e:
            logging.error(f"TheSky64 Socket Error: {e}")
            return "Error"

    # Mimic the methods/properties OmegaLambda expects
    def SlewToRaDecAsync(self, ra, dec, target_name="Target"):
        js = f"sky6RASCOMTele.SlewToRaDecAsync({ra}, {dec}, '{target_name}');"
        return self.send_js(js)

    @property
    def IsSlewComplete(self):
        js = "var res = sky6RASCOMTele.IsSlewComplete; res;"
        val = self.send_js(js)
        return int(val) if val.isdigit() else 1

    def SetTracking(self, tracking_on, transmission, ra_rate, dec_rate):
        js = f"sky6RASCOMTele.SetTracking({tracking_on}, {transmission}, {ra_rate}, {dec_rate});"
        return self.send_js(js)

    def Park(self):
        return self.send_js("sky6RASCOMTele.Park();")

    def Unpark(self):
        return self.send_js("sky6RASCOMTele.Unpark();")