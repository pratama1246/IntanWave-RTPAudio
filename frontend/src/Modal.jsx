import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

export default function Modal({ title, description, onClose, size = 'md', role = 'dialog', footer, children }) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    const first = role === 'alertdialog' ? dialog.querySelector('.modal-body button') : dialog.querySelector('input, textarea, button, [tabindex="0"]');
    (first || dialog).focus();
    const onKeyDown = event => {
      const dialogs = document.querySelectorAll('[data-modal-dialog]');
      if (dialogs[dialogs.length - 1] !== dialog) return;
      if (event.key === 'Escape' && dialog.querySelector('[aria-expanded="true"]')) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeRef.current();
      }
      if (event.key !== 'Tab') return;
      const controls = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')].filter(item => item.getClientRects().length);
      const firstControl = controls[0];
      const lastControl = controls[controls.length - 1];
      if (!firstControl) { event.preventDefault(); dialog.focus(); return; }
      if (event.shiftKey && (document.activeElement === firstControl || document.activeElement === dialog)) { event.preventDefault(); lastControl.focus(); }
      else if (!event.shiftKey && (document.activeElement === lastControl || document.activeElement === dialog)) { event.preventDefault(); firstControl.focus(); }
    };
    document.addEventListener('keydown', onKeyDown, true);
    return () => { document.removeEventListener('keydown', onKeyDown, true); if (previousFocus?.isConnected) previousFocus.focus(); };
  }, []);

  return (
    <div className="modal-overlay modal-shell">
      <section ref={dialogRef} data-modal-dialog role={role} aria-modal="true" aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined} tabIndex={-1} className={'modal-dialog modal-size-' + size}>
        <header className="modal-header">
          <div><h2 id={titleId}>{title}</h2>{description && <p id={descriptionId}>{description}</p>}</div>
          <button type="button" onClick={onClose} className="modal-close" aria-label="Tutup modal"><X size={18} /></button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer modal-actions">{footer}</div>}
      </section>
    </div>
  );
}
