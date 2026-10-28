import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, CircleDashed } from 'lucide-react';

const STEPS = [
  "Uploading project...",
  "Detecting language...",
  "Detecting framework...",
  "Parsing files using Tree-sitter...",
  "Running structure analysis...",
  "Calculating readiness score..."
];

export const Progress: React.FC = () => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    let current = 0;
    const interval = setInterval(() => {
      current = (current + 1) % (STEPS.length + 1);
      setCurrentStepIndex(current);
    }, 800);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] w-full max-w-2xl mx-auto px-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-dark border border-border-dark rounded-2xl p-10 w-full shadow-vscode"
      >
        <h2 className="text-2xl font-bold mb-8 text-center tracking-tight">Analyzing Project</h2>
        
        <div className="space-y-6">
          {STEPS.map((step, index) => {
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;
            const isFuture = index > currentStepIndex;

            return (
              <motion.div 
                key={step}
                initial={{ opacity: 0, x: -10 }}
                animate={{ 
                  opacity: isFuture ? 0.4 : 1,
                  x: 0,
                  scale: isCurrent ? 1.02 : 1
                }}
                transition={{ duration: 0.3 }}
                className={`flex items-center gap-4 ${isCurrent ? 'text-primary-brand' : isCompleted ? 'text-primary-dark' : 'text-secondary-dark'}`}
              >
                <div className="flex-shrink-0">
                  {isCompleted ? (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 20 }}
                    >
                      <CheckCircle2 className="text-status-verified" size={24} />
                    </motion.div>
                  ) : isCurrent ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                    >
                      <CircleDashed size={24} />
                    </motion.div>
                  ) : (
                    <CircleDashed size={24} className="opacity-50" />
                  )}
                </div>
                <span className={`text-lg font-medium ${isCompleted ? 'text-primary-dark' : isCurrent ? 'text-primary-brand' : ''}`}>
                  {step}
                </span>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
};
