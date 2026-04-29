const fs = require('fs');

const MAC_ARM_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function chromeExecutablePath() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    return process.env.PUPPETEER_EXECUTABLE_PATH;
  }
  if (process.platform === 'darwin' && process.arch === 'arm64' && fs.existsSync(MAC_ARM_CHROME)) {
    return MAC_ARM_CHROME;
  }
  return undefined;
}

function launchOptions(options = {}) {
  const executablePath = chromeExecutablePath();
  return executablePath ? { ...options, executablePath } : options;
}

module.exports = {
  MAC_ARM_CHROME,
  chromeExecutablePath,
  launchOptions,
};
