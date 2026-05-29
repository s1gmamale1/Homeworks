import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// If frames flicker on Windows, drop concurrency: Config.setConcurrency(1);
