import { forwardRef, InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onCheckedChange'> {
  onCheckedChange?: (checked: boolean) => void;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, onCheckedChange, ...props }, ref) => {
    return (
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          ref={ref}
          className="sr-only peer"
          onChange={(e) => onCheckedChange?.(e.target.checked)}
          {...props}
        />
        <div
          className={cn(
            'h-5 w-5 rounded border-2 border-gray-300 bg-white',
            'peer-checked:bg-blue-600 peer-checked:border-blue-600',
            'peer-focus-visible:ring-2 peer-focus-visible:ring-blue-600 peer-focus-visible:ring-offset-2',
            'flex items-center justify-center transition-colors',
            className
          )}
        >
          <Check className="h-3.5 w-3.5 text-white opacity-0 peer-checked:opacity-100" />
        </div>
      </label>
    );
  }
);

Checkbox.displayName = 'Checkbox';
