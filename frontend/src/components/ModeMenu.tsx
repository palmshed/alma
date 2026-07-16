// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState, useRef, useEffect } from 'react';
import { Layers, Sparkles, Globe, Image } from 'lucide-react';
import type { ModeOption } from '../types';
import { findScrollParent } from '../utils/overflow';

const ICONS: Record<string, React.ReactNode> = {
  layers: <Layers size={15} strokeWidth={1.7} />,
  sparkles: <Sparkles size={15} strokeWidth={1.7} />,
  globe: <Globe size={15} strokeWidth={1.7} />,
  image: <Image size={15} strokeWidth={1.7} />,
};

interface ModeMenuProps {
  options: ModeOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

const ModeMenu: React.FC<ModeMenuProps> = ({ options, value, onChange, disabled }) => {
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
    <div className="mode-menu" ref={menuRef}>
      <button
        className="mode-menu-trigger"
        onClick={() => setOpen(!open)}
        disabled={disabled}
        type="button"
        aria-label={`Mode: ${active.label}`}
        aria-expanded={open}
      >
        {ICONS[active.icon]}
      </button>
      {open && (
        <div className="mode-menu-dropdown" role="menu">
          {options.map((opt) => {
            const isActive = opt.value === value;
            return (
              <button
                key={opt.value}
                className={`mode-menu-item${isActive ? ' active' : ''}`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
                role="menuitemradio"
                aria-checked={isActive}
                type="button"
              >
                <span className="mode-menu-item-icon">{ICONS[opt.icon]}</span>
                <span className="mode-menu-item-label">{opt.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ModeMenu;
