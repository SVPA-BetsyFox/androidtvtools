// Requires the webdriverio client library
// (npm install webdriverio)

const wdio = require('webdriverio');
const caps = {
  "platformName": "Android",
  "appActivity": "com.google.android.apps.youtube.tv.cobalt.activity.MainActivity",
  "appPackage": "com.google.android.youtube.tv",
  "deviceName": "Android TV"
};

const driver = wdio.remote({
  host: "localhost",
  port: 4723,
  desiredCapabilities: caps
});

    driver.init()
    console.log(typeof driver.contexts());
    driver.end();