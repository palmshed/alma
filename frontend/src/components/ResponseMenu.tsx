import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import type { ResponseOption } from '../types';
import { findScrollParent } from '../utils/overflow';

interface ResponseMenuProps {
  options: ResponseOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

const ResponseMenu: React.FC<ResponseMenuProps> = ({ options, value, onChange, disabled }) => {
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
    <div className="response-menu" ref={menuRef}>
      <button
        className="response-menu-trigger"
        onClick={() => setOpen(!open)}
        disabled={disabled}
        type="button"
        aria-label={`Response: ${active.label}`}
        aria-expanded={open}
      >
        <span className="response-menu-trigger-label">{active.label}</span>
        <ChevronDown size={10} strokeWidth={1.7} />
      </button>
      {open && (
        <div className="response-menu-dropdown" role="menu">
          {options.map((opt) => {
            const isActive = opt.value === value;
            return (
              <button
                key={opt.value}
                className={`response-menu-item${isActive ? ' active' : ''}`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
                role="menuitemradio"
                aria-checked={isActive}
                type="button"
              >
                <span className="response-menu-item-label">{opt.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ResponseMenu;
