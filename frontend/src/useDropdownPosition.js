import { useLayoutEffect, useState } from 'react';

export default function useDropdownPosition(isOpen, containerRef, preferredWidth = 240) {
  const [position, setPosition] = useState({});
  useLayoutEffect(() => {
    if (!isOpen) return;
    const update = () => {
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const scrollArea = container.closest('.modal-body');
      const bounds = scrollArea?.getBoundingClientRect();
      const top = Math.max(12, bounds?.top ?? 12);
      const bottom = Math.min(window.innerHeight - 12, bounds?.bottom ?? window.innerHeight - 12);
      const above = rect.top - top;
      const below = bottom - rect.bottom;
      const opensUp = below < 320 && above > below;
      const left = Math.max(12, bounds?.left ?? 12);
      const right = Math.min(window.innerWidth - 12, bounds?.right ?? window.innerWidth - 12);
      const width = Math.min(Math.max(rect.width, preferredWidth), right - left);
      const offset = Math.max(left - rect.left, Math.min(0, right - rect.left - width));
      setPosition({ width: width + 'px', maxWidth: width + 'px', minWidth: 0, left: offset + 'px', right: 'auto', top: opensUp ? 'auto' : 'calc(100% + 6px)', bottom: opensUp ? 'calc(100% + 6px)' : 'auto', marginTop: 0, maxHeight: Math.max(80, Math.min(380, (opensUp ? above : below) - 12)) + 'px', overflowY: 'auto' });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => { window.removeEventListener('resize', update); window.removeEventListener('scroll', update, true); };
  }, [isOpen, containerRef, preferredWidth]);
  return position;
}
