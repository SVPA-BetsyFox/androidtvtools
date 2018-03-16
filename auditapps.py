import subprocess

class obj:
   def __init__(self, **attributes):
      self.__dict__.update(attributes)


def init():
  args.forEach(arg => {
    print(f'Connecting to {arg}')
    if (!connect(arg)):
      error(f'Unable to connect to {arg}.')


def adb(serial, command):
  out = execute(f'adb -s {serial} {command}')
  if (out):
    return out
  else:
    error(f'Connection to {serial} lost, reconnecting...')
    if (connect(serial)):
      return adb(serial, command)
    else:
      error("Failed to connect!")
      return false


def connect(serial, port):
  if (port):
    serial = f'{serial}:{port}'
  status = execute(f'adb connect {serial}')
  return !(status.indexOf("unable") > -1)


def execute(cmd):
  print("#### ===> EXECUTING " + cmd)
  out = subprocess.check_output(cmd)
  return out



def get_devices():
  raw = execute("adb devices -l")
  raw = raw.split("\n")
  raw.pop(0)
  raw = filter(lambda e: e.strip() != '', raw)
  count = raw.length, i = 0
  raw = raw.map(e => {
    progress(++i, count)
    e = e.split(/\s+/)
    id = e.pop(0)
    type = e.pop(0)
    data = {}
    e.forEach(item => {
      [label, value] = item.split(":")
      data[label] = value
    })
    return {id: id, type: type, ...data}
  })
  return raw


def get_package_ver(serial="NONE", package):
  raw = adb(serial, f'shell dumpsys package {package} | grep versionName').split("\n")[0]
  return raw.slice(raw.indexOf("=") + 1).strip()


def get_package_info(serial="NONE", package):
  return adb(serial, f'shell dumpsys package {package}')


def get_active_app(serial="NONE"):
  regex = /(?:\{)(\w+)\s(\w+)\s(.+)(?:\})/
  rawCurrentFocus = adb(serial, f'shell dumpsys window windows | grep -E mCurrentFocus')
  [package, activity] = regex.exec(rawCurrentFocus)[3].split("/")
  return { appPackage: package, appActivity: activity }


def _app_info(x):
  x = x.replace("package:", "")
  info = x.split("=")
  version = get_package_ver(serial, info[1])
  rawinfo = get_package_info(serial, info[1])
  return obj(**{ "apk": info[0], "package": info[1], "version": version, "rawinfo": rawinfo })


def get_apps(serial="NONE"):
  raw = execute(f'adb -s {serial} shell pm list packages -f').split(/\r*\n/)
  count = raw.length, i = 1

  # skip blanks, grab apk, package name, and version for each hit
  raw = filter(lambda x: x != "", raw)
  raw.sort()
  map(lambda x: 
    package = x.slice(x.indexOf(":") + 1).split("=").pop()
    apk = x.slice(x.indexOf(":") + 1, x.lastIndexOf("="))
    version = get_package_ver(serial, package)
    rawinfo = get_package_info(serial, package)
    progress_bar(++i, count, 33, package)
    return { apk: apk, package: package, version: version, rawinfo: rawinfo }
  })
  progress_bar(1, 1, 33, "Processing report...")
  return raw


report = {}
init()

devices = get_devices()

if (devices.length < 1)  {
  error("Unable to connect to any devices.")
  process.exit(1)
}

devices.forEach(device => {
  print()
  print(f'Enumerating apps on {device.id}...')
  report[device.id] = {}
  device["activeApp"] = get_active_app(device.id)
  report[device.id]["device"] = device
  report[device.id]["apps"] = get_apps(device.id)
})

report_json = JSON.stringify(report, null, 2)
print(report_json)
process.stdout.write('\x1B[?25h\r')