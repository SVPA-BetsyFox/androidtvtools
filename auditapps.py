import subprocess, re, time, codecs, sys, json, hashlib, inspect, random, functools
import urllib.request
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
DEBUG = False
DUMMY = False
# DUMMY = True

sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)

prop_mapping = {
  'serialno': 'ro.serialno',
  'make': 'ro.product.brand',
  'model': 'ro.svp.modelname',
  'series': 'ro.svp.modelseries',
  'ipaddress': 'dhcp.wlan0.ipaddress',
  'panelsize': 'ro.svp.panel_inch'
}


# def get_app_name(package):
#   filename = "package_names.json"
#   names = load_report(filename) or {}
#   if package in names:
#     return names[package]
#   else:
#     try:
#       contents = urllib.request.urlopen(f'https://play.google.com/store/apps/details?id={package}').read().decode("utf-8")
#       title = re.search("<title.*?>(?P<name>.+?) - .+?</title>", contents).group("name")
#     except Exception as e:
#       title = False
#   names[package] = title
#   save_report(filename, names)
#   return title


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
  debug(cmd)
  out = subprocess.check_output(cmd)
  return out.decode('utf-8')

def adb(serial, cmd):
  return execute(f'adb -s {serial} {cmd}'.split(" "))

def connect(serial, port=5555):
  status = execute(f'adb connect {serial}:{port}'.split(" "))
  return (not(status.find("unable") > -1))

def get_package_ver(serial, package):
  raw = adb(serial, f'shell dumpsys package {package.strip()} | grep versionName')
  return raw[raw.find("=")+1:].strip()


def process_app(serial, app_data, count):
  print("called process app for serial " + serial)
  i = app_data[0]
  app_data = app_data[1].strip()
  app_data = app_data.replace("package:", "")
  info = app_data.split("=")
  version = get_package_ver(serial, info[1])
  # can_open = random.choice([True, False])
  out = { "apk": info[0], "package": info[1], "version": version, "serial": serial, "can_open": can_open_app(serial, info[1]), "is_updated": False }
  print(out)
  return out



def get_apps(serial):
  raw = execute(f'adb -s {serial} shell pm list packages -f'.split(" ")).split("\n")
  count = len(raw)
  out = {}
  apps = filter(lambda x: x != "", raw)
  apps = list(map(lambda x: process_app(serial, x, count), enumerate(apps)))
  last_report = load_report("report.json")
  for app in apps:
    if last_report[serial]['apps'][app['package']]['version'] != app["version"]:
      app['is_updated'] = True
    out[app["package"]] = app
  return out



def get_device_prop(serial):
  raw = execute(f'adb -s {serial} shell getprop'.split(" "))
  raw = raw.split("\n")
  out = {}
  for entry in raw:
    if(entry):
      key, value = entry.strip().split(": ")
      out[key[1:-1]] = value[1:-1]
  return out


def send_key_event(serial, event_id):
  try:
    raw = execute(f'adb -s {serial} shell input keyevent {event_id}'.split(" "))
    return True
  except Exception as e:
    print(e)
    return False


def is_device_awake(serial):
  data = get_device_awake_state(serial)
  out = ((data["display"] == "ON") and (data["wakefulness"] == "Awake"))
  return out


def get_device_awake_state(serial):
  raw = execute(['adb', '-s', serial, 'shell', 'dumpsys power | grep -e "mWakefulness=" -e "Display Power"']).strip().split("\n")
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



def open_app(serial, package):
  raw = execute(f'adb -s {serial} shell monkey -p {package} 1'.split(" "))
  return "No activities found to run" in raw

def can_open_app(serial, package):
  filename = "open_blacklist.json"
  open_blacklist = load_report(filename) or []
  if package in open_blacklist:
    return False
  else:
    raw = execute(f'adb -s {serial} shell monkey -p {package} 0'.split(" "))
    if "No activities found to run" in raw:
      open_blacklist.append(package)
      save_report(filename, open_blacklist)
      return False
    else:
      return True


# def dummy_report(lol):
#   serial = "dummy"
#   report = {}
#   report[serial] = {}
#   last_report = load_report("report.json")
#   print(last_report)
#   for app_i, app in enumerate(last_report[serial]['apps']):
#     adds_report_entry(last_report[serial]['apps'][app], app_i)


def clean_string(s):
  return re.sub("[^a-zA-Z0-9.-_/]", "", s)



def gen_report(ip):
  connect(ip)
  devices = get_devices()
  report = {}
  for device in devices:
    if not DUMMY:
      if not(is_device_awake(device)):
        print("DEVICE IS OFF, POWERING ON...")
        send_key_event(device, 26)
        attempts = 10
        while not(is_device_awake(device)) and (attempts > 0):
          attempts -= 1
          time.sleep(1)
          status = get_device_awake_state(device)
        if is_device_awake(device):
          print("DEVICE IS ON")

      props = get_device_prop(device)

      report[device] = {}
      count = len(prop_mapping)
      i = 0
      for k, v in prop_mapping.items():
        i += 1
        report[device][k] = props.get(v, None)
      #######################################################################################################
      serial = report[device]['serialno'] ###################################################################
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

##################################################################################################
from appJar import gui


def add_report_entry_text(package, ver, row, column, bg="#fff", fg="#000"):
  app.setSticky("ew")
  app.startFrame(f'_frame_[{package}_{ver}]', row=row, column=column)
  app.setFg(fg)
  app.setBg(bg)

  app.setSticky("w")
  app.startFrame(f'_frame_[{package}]_{ver}', row=0, column=0)
  app.addLabel(f'_[{package}]_{ver}', package)
  app.stopFrame()

  app.setSticky("e")
  app.startFrame(f'_frame__{package}_[{ver}]', row=0, column=1)
  app.addLabel(f'_{package}_[{ver}]', ver)
  app.stopFrame()

  app.stopFrame()


def add_report_entry(app_data={}, row=0):
  # debug("app_data")
  serial = app_data["serial"]
  package = clean_string(app_data["package"])
  version = clean_string(app_data["version"])
  apk = clean_string(app_data["apk"])
  is_updated = app_data["is_updated"]
  app.setSticky("ew")
  app.openScrollPane("app_report")
  app.setSticky("ew")
  bg = "#fff" if (row % 2 == 0) else "#ccc"
  fg = "#c22" if is_updated else "#000"
  add_report_entry_text(package, version, row=row, column=0, bg=bg, fg=fg)
  if app_data['can_open']:
    app.addNamedButton("open app", f'{serial} {package}', handle_open_app, row=row, column=1)
  else:
    app.addLabel(f'label_{row}', "package contains no activities", row=row, column=1)
  app.stopScrollPane()


def threadulate(func):
  app.thread(func)

def handle_open_app(serial_package):
  [serial, package] = serial_package.split(" ")
  return open_app(serial, package)


def update_progress(percent, msg=None):
  # app.queueFunction(app.setMeter, "progress", percent, clean_string(msg) + " (" + "%.3g" % round(percent) + "%)")
  app.setMeter("progress", percent, clean_string(msg) + " (" + "%.3g" % round(percent) + "%)")



app = gui("Betsy's Android TV Tools, Yes!", "1280x1024")
app.setStretch("column")
app.setFont(15)
app.setLocation("CENTER")
app.setIcon('./baatty.gif')

app.setSticky("new")

app.addLabelEntry("ip address", row=0, column=0)
app.setEntry("ip address", "172.30.7.97")

app.addButton("Yoink!", lambda: gen_report(app.getEntry("ip address")), row=0, column=1)

app.setSticky("news")
app.setStretch("both")
app.startScrollPane("app_report", row=1, colspan=2, rowspan=2)

app.setBg("#beeeef")
app.stopScrollPane()


app.setSticky("sew")
app.addMeter("progress", row=2, colspan=2)
app.setMeterFill("progress", "blue")
app.setMeterBg("progress", "black")
app.setMeterFg("progress", "gold")


try:
  app.go()
except Exception as e:
  pass




