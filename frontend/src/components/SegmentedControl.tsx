import React from 'react';
import { Layers, Sparkles, Globe, Image } from 'lucide-react';

interface Option {
  value: string;
  label: string;
  icon?: string;
}

interface SegmentedControlProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

const ICONS: Record<string, React.ReactNode> = {
  layers: <Layers size={13} strokeWidth={1.7} />,
  sparkles: <Sparkles size={13} strokeWidth={1.7} />,
  globe: <Globe size={13} strokeWidth={1.7} />,
  image: <Image size={13} strokeWidth={1.7} />,
};

const SegmentedControl: React.FC<SegmentedControlProps> = ({
  options,
  value,
  onChange,
  disabled,
}) => (
  <div className="segmented-control" role="radiogroup">
    {options.map((opt) => {
      const isActive = opt.value === value;
      return (
        <button
          key={opt.value}
          className={`segmented-control-btn${isActive ? ' active' : ''}`}
          onClick={() => onChange(opt.value)}
          disabled={disabled}
          role="radio"
          aria-checked={isActive}
          type="button"
        >
          {opt.icon && (
            <span className="segmented-control-icon">{ICONS[opt.icon]}</span>
          )}
          <span className="segmented-control-label">{opt.label}</span>
        </button>
      );
    })}
  </div>
);

export default SegmentedControl;
