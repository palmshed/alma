import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import type { ModelOption, ModelAvailability } from '../types';
import { findScrollParent } from '../utils/overflow';

interface ModelMenuProps {
  options: ModelOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  availability?: Record<string, ModelAvailability>;
}

const STATUS_LABELS: Record<string, string> = {
  ready: '',
  'cooling-down': 'Cooling down',
  unavailable: 'Unavailable',
};

const ModelMenu: React.FC<ModelMenuProps> = ({ options, value, onChange, disabled, availability }) => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const overflowParent = useRef<HTMLElement | null>(null);
  const active = options.find((o) => o.value === value) ?? options[0];

  const prevOverflow = useRef<string>('');

  useEffect(() => {
    if (open && menuRef.current) {
      overflowParent.current = findScrollParent(menuRef.current);
      if (overflowParent.current) {
        prevOverflow.current = overflowParent.current.style.overflow || '';
        overflowParent.current.style.overflow = 'visible';
      }
    }
    if (!open && overflowParent.current) {
      overflowParent.current.style.overflow = prevOverflow.current;
      overflowParent.current = null;
      prevOverflow.current = '';
    }
  }, [open]);

  useEffect(() => {
    return () => {
      if (overflowParent.current) {
        overflowParent.current.style.overflow = prevOverflow.current;
      }
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="model-menu" ref={menuRef}>
      <button
        className="model-menu-trigger"
        onClick={() => setOpen(!open)}
        disabled={disabled}
        type="button"
        aria-label={`Model: ${active.label}`}
        aria-expanded={open}
      >
        <span className="model-menu-trigger-label">{active.shortLabel || active.label}</span>
        <ChevronDown size={12} strokeWidth={1.7} />
      </button>
      {open && (
        <div className="model-menu-dropdown" role="menu">
          {options.map((opt) => {
            const isActive = opt.value === value;
            const av = availability?.[opt.value];
            return (
              <button
                key={opt.value}
                className={`model-menu-item${isActive ? ' active' : ''}`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
                role="menuitemradio"
                aria-checked={isActive}
                type="button"
                disabled={av?.state === 'unavailable'}
              >
                <span className="model-menu-item-label">{opt.label}</span>
                {av && av.state !== 'ready' && (
                  <span className={`model-menu-item-status model-menu-item-status--${av.state}`}>
                    {STATUS_LABELS[av.state]}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ModelMenu;
