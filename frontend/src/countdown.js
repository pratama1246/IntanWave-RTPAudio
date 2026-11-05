export function startCountdown(seconds, onTick, onComplete) {
  let remaining = seconds;
  onTick(remaining);
  const timer = setInterval(() => {
    remaining -= 1;
    onTick(remaining);
    if (remaining === 0) {
      clearInterval(timer);
      onComplete();
    }
  }, 1000);
  return () => clearInterval(timer);
}
