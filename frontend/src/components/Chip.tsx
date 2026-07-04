import React from 'react';

interface ChipProps {
  label: string;
  onClick?: () => void;
  selected?: boolean;
  disabled?: boolean;
}

const Chip: React.FC<ChipProps> = ({ label, onClick, selected, disabled }) => (
  <button
    className={`chip${selected ? ' chip--selected' : ''}`}
    onClick={onClick}
    disabled={disabled}
    type="button"
  >
    {label}
  </button>
);

export default Chip;
