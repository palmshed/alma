import { ReactNode } from 'react';

interface LandingLayoutProps {
  hero: ReactNode;
  composer: ReactNode;
  suggestions?: ReactNode;
  modes: ReactNode;
}

export default function LandingLayout({ hero, composer, suggestions, modes }: LandingLayoutProps) {
  return (
    <main className="landing">
      <div className="landing-inner">
        <div className="landing-brand">
          {hero}
        </div>
        <div className="landing-composer">
          {composer}
          {suggestions}
          {modes}
        </div>
      </div>
    </main>
  );
}
