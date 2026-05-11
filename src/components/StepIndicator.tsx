import { useAppState } from '../context/AppContext';

const steps = [
  { num: 1, label: 'Select & Review', short: 'Files' },
  { num: 2, label: 'Layout & Preview', short: 'Layout' },
  { num: 3, label: 'Review & Download', short: 'Download' },
];

export default function StepIndicator() {
  const { state } = useAppState();
  const currentStep = state.step;

  return (
    <div className="flex items-center justify-center gap-2 py-4 px-4 bg-white border-b border-slate-200">
      {steps.map((step, i) => {
        const isActive = step.num === currentStep;
        const isDone = step.num < currentStep;
        return (
          <div key={step.num} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={`w-8 h-0.5 ${isDone ? 'bg-blue-500' : 'bg-slate-300'}`}
              />
            )}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-500 text-white'
                  : isDone
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-slate-100 text-slate-400'
              }`}
            >
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                  isActive
                    ? 'bg-white text-blue-500'
                    : isDone
                      ? 'bg-blue-500 text-white'
                      : 'bg-slate-300 text-slate-500'
                }`}
              >
                {isDone ? '✓' : step.num}
              </span>
              <span className="hidden sm:inline">{step.label}</span>
              <span className="sm:hidden">{step.short}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
