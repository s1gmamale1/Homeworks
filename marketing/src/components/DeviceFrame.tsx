import {Img, staticFile} from 'remotion';

type Props = {
  src: string;
  kind?: 'browser' | 'laptop' | 'phone';
  width: number;
  radius?: number;
};

export const DeviceFrame: React.FC<Props> = ({
  src,
  kind = 'browser',
  width,
  radius = 18,
}) => {
  const bar = kind === 'phone' ? 0 : 36;
  return (
    <div
      style={{
        width,
        borderRadius: radius + 8,
        background: '#1d1d1f',
        padding: 10,
        boxShadow: '0 40px 120px rgba(0,0,0,0.45)',
      }}
    >
      {bar > 0 && (
        <div
          style={{
            height: bar,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '0 14px',
          }}
        >
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
            <span
              key={c}
              style={{width: 12, height: 12, borderRadius: '50%', background: c}}
            />
          ))}
        </div>
      )}
      <Img
        src={staticFile(`shots/${src}`)}
        style={{
          width: '100%',
          display: 'block',
          borderRadius: radius,
          objectFit: 'cover',
        }}
      />
    </div>
  );
};
