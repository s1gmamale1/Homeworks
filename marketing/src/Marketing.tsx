import {AbsoluteFill, Audio, interpolate, Sequence, staticFile} from 'remotion';
import './theme/fonts';
import {SCENES} from './theme/tokens';
import {Backdrop} from './components/Backdrop';
import {Scene0Hook} from './scenes/Scene0Hook';
import {Scene1Problem} from './scenes/Scene1Problem';
import {Scene2Reveal} from './scenes/Scene2Reveal';
import {Scene3Teacher} from './scenes/Scene3Teacher';
import {Scene4Student} from './scenes/Scene4Student';
import {Scene5Tutor} from './scenes/Scene5Tutor';
import {Scene6Outcomes} from './scenes/Scene6Outcomes';
import {Scene7Proof} from './scenes/Scene7Proof';
import {Scene8CTA} from './scenes/Scene8CTA';

const HAS_MUSIC = true; // set false if no track.mp3 is present

export const Marketing: React.FC<{lang: 'uz'}> = () => {
  const S = SCENES;
  return (
    <AbsoluteFill>
      <Backdrop />
      <Sequence from={S.hook.from} durationInFrames={S.hook.duration} name="Hook">
        <Scene0Hook />
      </Sequence>
      <Sequence from={S.problem.from} durationInFrames={S.problem.duration} name="Problem">
        <Scene1Problem />
      </Sequence>
      <Sequence from={S.reveal.from} durationInFrames={S.reveal.duration} name="Reveal">
        <Scene2Reveal />
      </Sequence>
      <Sequence from={S.teacher.from} durationInFrames={S.teacher.duration} name="Teacher">
        <Scene3Teacher />
      </Sequence>
      <Sequence from={S.student.from} durationInFrames={S.student.duration} name="Student">
        <Scene4Student />
      </Sequence>
      <Sequence from={S.tutor.from} durationInFrames={S.tutor.duration} name="Tutor">
        <Scene5Tutor />
      </Sequence>
      <Sequence from={S.outcomes.from} durationInFrames={S.outcomes.duration} name="Outcomes">
        <Scene6Outcomes />
      </Sequence>
      <Sequence from={S.proof.from} durationInFrames={S.proof.duration} name="Proof">
        <Scene7Proof />
      </Sequence>
      <Sequence from={S.cta.from} durationInFrames={S.cta.duration} name="CTA">
        <Scene8CTA />
      </Sequence>
      {HAS_MUSIC && (
        <Audio
          src={staticFile('audio/track.mp3')}
          volume={(f) =>
            interpolate(f, [0, 15, 2220, 2250], [0, 1, 1, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          }
        />
      )}
    </AbsoluteFill>
  );
};
