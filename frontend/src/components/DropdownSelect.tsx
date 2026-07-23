// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';

interface DropdownSelectProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}

const DropdownSelect: React.FC<DropdownSelectProps> = ({ options, value, onChange }) => {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; minWidth: number }>({ top: 0, left: 0, minWidth: 0 });
  const active = options.find((o) => o.value === value) ?? options[0];

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) return;
      if (menuRef.current?.contains(t)) return;
      close();
    };
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); close(); }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [open, close]);

  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const dropHeight = options.length * 32 + 12;
    const top = spaceBelow > dropHeight + 8
      ? rect.bottom + 4
      : rect.top - dropHeight - 4;
    let left = rect.left;
    const minWidth = rect.width;
    const menuWidth = Math.max(minWidth, 160);
    if (left + menuWidth > window.innerWidth - 8) {
      left = window.innerWidth - menuWidth - 8;
    }
    if (left < 8) left = 8;
    setPos({ top, left, minWidth });
  }, [open, options.length]);

  return (
    <>
      <button
        ref={triggerRef}
        className="model-menu-trigger"
        onClick={() => setOpen(v => !v)}
        type="button"
        aria-label={active?.label}
        aria-expanded={open}
      >
        <span className="model-menu-trigger-label">{active?.label}</span>
        <ChevronDown size={12} strokeWidth={1.7} />
      </button>
      {open && createPortal(
        <div
          ref={menuRef}
          className="dropdown-select-menu"
          role="menu"
          style={{ position: 'fixed', top: pos.top, left: pos.left, minWidth: pos.minWidth, zIndex: 1000 }}
        >
          {options.map((opt) => {
            const isActive = opt.value === value;
            return (
              <button
                key={opt.value}
                className={`model-menu-item${isActive ? ' active' : ''}`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
                role="menuitemradio"
                aria-checked={isActive}
                type="button"
              >
                <span className="model-menu-item-label">{opt.label}</span>
              </button>
            );
          })}
        </div>,
        document.body
      )}
    </>
  );
};

export default DropdownSelect;
