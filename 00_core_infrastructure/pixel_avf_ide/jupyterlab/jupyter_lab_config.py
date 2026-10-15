# Configuration file for JupyterLab on Pixel AVF Linux microVM
c = get_config()

c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.allow_remote_access = True
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.disable_check_xsrf = True
c.ServerApp.root_dir = '/mnt/shared'
c.LabApp.default_url = '/lab'
c.ServerApp.max_buffer_size = 536870912
