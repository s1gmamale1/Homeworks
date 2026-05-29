import {FONT, WHITE} from '../theme/tokens';
import {ClassALogo} from './ClassALogo';

type Props = {
  logoSize?: number;
  color?: string;
  fontSize?: number;
  progress?: number;
  twinkle?: number;
  layout?: 'row' | 'col';
};

export const Wordmark: React.FC<Props> = ({
  logoSize = 140,
  color = WHITE,
  fontSize = 56,
  progress = 1,
  twinkle = 1,
  layout = 'row',
}) => (
  <div
    style={{
      display: 'flex',
      flexDirection: layout === 'row' ? 'row' : 'column',
      alignItems: 'center',
      gap: layout === 'row' ? 28 : 18,
    }}
  >
    <ClassALogo size={logoSize} progress={progress} twinkle={twinkle} />
    <div
      style={{
        fontFamily: FONT.display,
        fontWeight: 700,
        fontSize,
        color,
        letterSpacing: '-0.02em',
        lineHeight: 1,
      }}
    >
      Class A <span style={{opacity: 0.85}}>Education</span>
    </div>
  </div>
);
