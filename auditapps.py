import os, subprocess, re, time, codecs, sys, json, hashlib, inspect, random, functools
import urllib.request
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
DEBUG = False
DUMMY = False
GO_BUTTON = "yoink"

SUBSEQUENT_REPORT = False

###########################################
#   GLOBAL STUFF JUST LIKE THE OLD DAYS   #
###########################################
DEVICE = {}
SERIAL = ""
IP = ""

sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)

prop_mapping = {
  'serialno': 'ro.serialno',
  'make': 'ro.product.brand',
  'model': 'ro.svp.modelname',
  'series': 'ro.svp.modelseries',
  'ipaddress': 'dhcp.wlan0.ipaddress',
  'panelsize': 'ro.svp.panel_inch'
}


def load_report(filename):
  try:
    f = open(filename, 'r')
    s = f.read()
    f.close()
    return json.loads(s)
  except Exception as e:
    return False


def save_report(filename, report):
  f = open(filename, 'w')
  f.write(json.dumps(report))
  f.close()


def debug(msg):
  if DEBUG:
    [frame, filename, lineno, caller, context, index] = inspect.stack()[2]
    print(f'=== from {caller} on {lineno} '.ljust(74, '=') + '----->')
    print(msg)
    print('----->'.rjust(80, '='))
  # if DEBUG:
  #   caller = inspect.stack()[1][3]
  #   print(f'CALLED DEBUG: {msg}')


def execute(cmd):
  whitelist = ['adb', 'connect', 'get_devices']
  [frame, filename, lineno, caller, context, index] = inspect.stack()[1]
  if caller not in whitelist:
    print(f'execute was called from from {caller} on {lineno} '.ljust(74, '=') + '! =====----->')
  debug(cmd)
  out = subprocess.check_output(cmd)
  return out.decode('utf-8')

def adb(ip, cmd):
  print(f'Called adb for ip: "{ip}", command: "{cmd}"')
  if ip not in get_devices():
    connect(*ip.split(":"))
  return execute(f'adb -s {ip} {cmd}'.split(" "))

def connect(ip, port=5555, max_attempts=3):
  attempts = 0
  status = False
  while not status and attempts < max_attempts:
    attempts += 1
    if f'{ip}:{port}' not in get_devices():
      debug(f'Connecting to {ip}:{port}, attempt #{attempts}/{max_attempts}...')
      status = (not(execute(f'adb connect {ip}:{port}'.split(" ")).find("unable") > -1))
    else:
      status = True
  return status


def wake(ip):
  if not(is_device_awake(ip)):
    print(f'Device ({ip}) is off, powering on...')
    send_key_event(ip, 26)
    attempts = 10
    while not(is_device_awake(ip)) and (attempts > 0):
      attempts -= 1
      time.sleep(1)
      status = get_device_awake_state(ip)
    if is_device_awake(ip):
      print(f'Device: ({ip}) is on!')
      return True
  else: # already on!
    return True
  return False


def is_updated(ip, package, version):
  global SERIAL
  last_report = load_report("report.json")
  print(f' WE\'RE COMPARING PACKAGE {package}!')
  print(f' OLD VER: {version} | NEW VER: {last_report[SERIAL]["apps"][package]["version"]}')
  if (SERIAL not in last_report) or (version != last_report[SERIAL]["apps"][package]["version"]):
    return True
  else:
    return False


def get_package_ver(ip, package):
  raw = adb(ip, f'shell dumpsys package {package.strip()} | grep versionName')
  return raw[raw.find("=")+1:].strip()


def get_apps(ip):
  raw = adb(ip, 'shell pm list packages -f').split("\n")
  count = len(raw)
  out = {}
  apps = filter(lambda x: x != "", raw)
  apps = list(map(lambda x: process_app(ip, x, count), enumerate(apps)))
  for app in apps:
    out[app["package"]] = app
  return out



def get_device_prop(ip):
  raw = adb(ip, 'shell getprop')
  raw = raw.split("\n")
  out = {}
  for entry in raw:
    if(entry):
      key, value = entry.strip().split(": ")
      out[key[1:-1]] = value[1:-1]
  return out


def send_key_event(ip, event_id):
  try:
    raw = adb(ip, f'shell input keyevent {event_id}')
    return True
  except Exception as e:
    print(e)
    return False


def is_device_awake(ip):
  data = get_device_awake_state(ip)
  out = ((data["display"] == "ON") and (data["wakefulness"] == "Awake"))
  return out


def get_device_awake_state(ip):
  raw = adb(ip, 'shell dumpsys power | grep -e "mWakefulness=" -e "Display Power"').strip().split("\n")
  out = {}
  for line in raw:
    if line.startswith("Display"):
      out["display"] = line.strip().split("=")[-1]
    elif line.startswith("mWakefulness"):
      out["wakefulness"] = line.strip().split("=")[-1]
  return out


def get_devices():
  raw = execute("adb devices".split(" "))
  raw = raw.split("\n")
  raw.pop(0)
  raw = list(filter(lambda e: e.strip() != '', raw))
  raw = list(map(lambda x: x.split("\t")[0], raw))
  return raw


def process_app(ip, app_data, count):
  serial = ip
  debug("called process app for ip " + ip)
  i = app_data[0]
  app_data = app_data[1].strip()
  app_data = app_data.replace("package:", "")
  [apk, package] = app_data.split("=")
  version = get_package_ver(ip, package)
  updated = is_updated(ip, package, version)
  out = { "apk": apk, "package": package, "version": version, "can_open": can_open_app(serial, package), "updated": updated }
  update_progress((i / count) * 100, f'Processing app: {package}... ')
  debug(out)
  return out


def open_app(ip, package):
  # raw = execute(f'adb -s {ip} shell monkey -p {package} 1'.split(" "))
  print(f'CALLED OPEN_APP FOR IP: "{ip}", PACKAGE: "{package}"')
  print(f'shell monkey -p {package} 1')
  raw = adb(ip, f'shell monkey -p {package} 1')
  return "No activities found to run" in raw


def can_open_app(ip, package):
  filename = "open_blacklist.json"
  open_blacklist = load_report(filename) or []
  if package in open_blacklist:
    return False
  else:
    raw = adb(ip, f'shell monkey -p {package} 0')
    if "No activities found to run" in raw:
      open_blacklist.append(package)
      save_report(filename, open_blacklist)
      return False
    else:
      return True


def clean_string(s):
  return re.sub("[^a-zA-Z0-9.-_/]", "", s)

def gen_report():
  global SERIAL, IP, ui
  ui.setButtonState(GO_BUTTON, "disabled")
  ip = ui.getEntry("ip address")
  if SUBSEQUENT_REPORT:
    reset_ui(ip)
  print("BLOCKING CLICKS")
  connect(ip)
  devices = get_devices()
  report = {}
  if len(devices) < 1:
    update_progress(0, "FAILED TO CONNECT")
    return
  for device in devices:
    if not DUMMY:
      props = get_device_prop(device)

      report[device] = {}
      count = len(prop_mapping)
      i = 0
      for k, v in prop_mapping.items():
        i += 1
        report[device][k] = props.get(v, None)
      #############################################################################################
      serial = report[device]['serialno']
      SERIAL = serial
      IP = ip

      ########################################################
      report[serial] = report.pop(device) #renaming our primary key to the device serial number (was the IP!)
      #######################################################################################################
      report[serial]['apps'] = get_apps(device)
      save_report("report.json", report)
    else:
      report = load_report("report.json")
      serial = list(report.keys())[0]

    print(report)
    # the next few lines are dumb as hell, but this is the least stupid way i can think of to achieve
    # something that would be a single line in any other language... in any other lang, you can pass a
    # comparison function in order to perform sorts against complex objects (i.e. not a string or a number)
    # but this was removed in python 3, because reasons. 
    # 
    # there might be a way less stupid way of doing this but i have a migraine coming on right now
    report_order = []
    for app_i, app in enumerate(report[serial]['apps']):
      if report[serial]['apps'][app]['can_open']:
        can_open = "1"
      else:
        can_open = "X"
      report_order.append(can_open + app)
    report_order = sorted(report_order)

    # seriously all my wat
    # maybe i'll do a double take tomorrow.

    for app_i, app in enumerate(report_order):
      print(f'app is {app}, app_i is {app_i}')
      add_report_entry(report[serial]['apps'][app[1:]], app_i)
  update_progress(100, "Done!")


# def dummy_report(ip):
#   serial = "dummy"
#   report = {}
#   report[serial] = {}
#   last_report = load_report("report.json")
#   print(last_report)
#   for APP_i, APP in enumerate(last_report[serial]['apps']):
#     adds_report_entry(last_report[serial]['apps'][app], app_i)

##################################################################################################
from appJar import gui


def add_report_entry_text(package, ver, row, column, bg="#fff", fg="#000"):
  global ui
  ui.setSticky("ew")
  ui.startFrame(f'_frame_[{package}_{ver}]', row=row, column=column)
  ui.setFg(fg)
  ui.setBg(bg)

  ui.setSticky("w")
  ui.startFrame(f'_frame_[{package}]_{ver}', row=0, column=0)
  ui.addLabel(f'_[{package}]_{ver}', package)
  ui.stopFrame()

  ui.setSticky("e")
  ui.startFrame(f'_frame__{package}_[{ver}]', row=0, column=1)
  ui.addLabel(f'_{package}_[{ver}]', ver)
  ui.stopFrame()

  ui.stopFrame()


def add_report_entry(app_data={}, row=0):
  global ui
  package = clean_string(app_data["package"])
  version = clean_string(app_data["version"])
  apk = clean_string(app_data["apk"])
  updated = app_data["updated"]
  ui.setSticky("ew")
  ui.openScrollPane("app_report")
  ui.setSticky("ew")
  bg = "#fff" if (row % 2 == 0) else "#ccc"
  fg = "#c22" if updated else "#000"
  add_report_entry_text(package, version, row=row, column=0, bg=bg, fg=fg)
  if app_data['can_open']:
    ui.addNamedButton("open app", f'{IP} {package}', handle_open_app, row=row, column=1)
  else:
    ui.addLabel(f'label_{row}', "package contains no activities", row=row, column=1)
  ui.stopScrollPane()


# when passed a job that needs handled in another thread, this will run it in another thread

def threadulate(func, cb):
  global ui
  ui.threadCallback(func, cb)


def handle_open_app(ip_package):
  [ip, package] = ip_package.split(" ")
  return open_app(ip, package)


def update_progress(percent, msg=None):
  global ui
  ui.queueFunction(ui.setMeter, "progress", percent, clean_string(msg) + " (" + "%.3g" % round(percent) + "%)")



def initialize_ui():
  global ui
  ui = gui("Betsy's Android TV Tools, Yes!", "1280x1024")
  reset_ui()


def clear_ui():
  global ui
  ui.removeAllWidgets()

def allow_click(x):
  print("ALLOWING CLICKS AGAIN LOL")
  ui.setButtonState(GO_BUTTON, "normal")

def reset_ui(ip="172.30.7.97"):
  global ui
  clear_ui()
  ui.setStretch("column")
  ui.setFont(15)
  ui.setLocation("CENTER")

  ui.setSticky("news")

  ui.addLabelEntry("ip address", row=0, column=0)
  ui.setEntry("ip address", ip)

  ui.addButton(GO_BUTTON, lambda: threadulate(gen_report, allow_click), row=0, column=1)
  # ui.addButton("deeeeebug", lambda: clear_ui(), row=-1, column=2)

  ui.setSticky("news")
  ui.setStretch("both")
  ui.startScrollPane("app_report", row=1, colspan=2, rowspan=2)

  ui.setBg("#beeeef")
  ui.stopScrollPane()


  ui.setSticky("sew")
  # ui.addMeter("DUMMYPROGRESSLOL", row=2, colspan=2)
  ui.setStretch("none")
  ui.addMeter("progress", row=3, colspan=2)
  ui.setMeterFill("progress", "blue")
  ui.setMeterBg("progress", "black")
  ui.setMeterFg("progress", "gold")




initialize_ui()
try:
  ui.go()
except Exception as e:
  pass




