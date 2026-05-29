import {Composition} from 'remotion';
import {Marketing} from './Marketing';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ClassAMarketing"
      component={Marketing}
      durationInFrames={2250}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{lang: 'uz' as const}}
    />
  );
};
