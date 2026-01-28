/**
 * BookingWizard Component
 * Multi-step wizard for booking sessions with validation and preview
 */

import React from 'react';
import {
    ChevronRight,
    ChevronLeft,
    Check,
    Calendar,
    Clock,
    User,
    FileText,
    CreditCard,
    AlertCircle,
    Loader2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Wizard step configuration
export interface WizardStep {
    id: string;
    title: string;
    description: string;
    icon: React.ReactNode;
    isOptional?: boolean;
}

// Booking data interface
export interface BookingData {
    sessionType: string;
    date: string;
    time: string;
    duration: number;
    clientName: string;
    clientEmail: string;
    notes: string;
    paymentMethod?: string;
}

// Validation errors
export interface ValidationErrors {
    [field: string]: string | undefined;
}

interface BookingWizardProps {
    steps: WizardStep[];
    currentStep: number;
    bookingData: BookingData;
    errors: ValidationErrors;
    isSubmitting: boolean;
    onStepChange: (step: number) => void;
    onDataChange: (data: Partial<BookingData>) => void;
    onSubmit: () => void;
    onCancel: () => void;
    className?: string;
}

// Step indicator component
const StepIndicator: React.FC<{
    steps: WizardStep[];
    currentStep: number;
    onStepClick: (step: number) => void;
}> = ({ steps, currentStep, onStepClick }) => {
    return (
        <div className="flex items-center justify-center mb-8">
            {steps.map((step, index) => {
                const isCompleted = index < currentStep;
                const isCurrent = index === currentStep;
                const isClickable = index <= currentStep;

                return (
                    <React.Fragment key={step.id}>
                        {/* Step circle */}
                        <button
                            onClick={() => isClickable && onStepClick(index)}
                            disabled={!isClickable}
                            className={cn(
                                'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all',
                                isCompleted
                                    ? 'bg-green-500 border-green-500 text-white'
                                    : isCurrent
                                        ? 'border-brand-500 bg-brand-500/10 text-brand-500'
                                        : 'border-surface-600 text-surface-500',
                                isClickable && 'cursor-pointer hover:scale-105'
                            )}
                        >
                            {isCompleted ? (
                                <Check className="w-5 h-5" />
                            ) : (
                                <span className="font-medium">{index + 1}</span>
                            )}
                        </button>

                        {/* Connector line */}
                        {index < steps.length - 1 && (
                            <div
                                className={cn(
                                    'w-12 h-0.5 mx-2',
                                    index < currentStep ? 'bg-green-500' : 'bg-surface-700'
                                )}
                            />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
};

// Step header
const StepHeader: React.FC<{ step: WizardStep }> = ({ step }) => (
    <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-brand-500/10 text-brand-500 mb-3">
            {step.icon}
        </div>
        <h2 className="text-xl font-bold">{step.title}</h2>
        <p className="text-sm text-surface-400">{step.description}</p>
    </div>
);

// Form field wrapper with error display
const FormField: React.FC<{
    label: string;
    error?: string;
    required?: boolean;
    children: React.ReactNode;
}> = ({ label, error, required, children }) => (
    <div className="mb-4">
        <label className="block text-sm font-medium mb-1.5">
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        {children}
        {error && (
            <div className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                <AlertCircle className="w-3 h-3" />
                {error}
            </div>
        )}
    </div>
);

// Booking preview card
const BookingPreview: React.FC<{ data: BookingData }> = ({ data }) => (
    <div className="bg-surface-800 rounded-lg p-4 space-y-3">
        <h3 className="font-semibold text-sm text-surface-300">Booking Summary</h3>

        <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
                <span className="text-surface-500">Session Type</span>
                <p className="font-medium">{data.sessionType || 'Not selected'}</p>
            </div>
            <div>
                <span className="text-surface-500">Date</span>
                <p className="font-medium">{data.date || 'Not selected'}</p>
            </div>
            <div>
                <span className="text-surface-500">Time</span>
                <p className="font-medium">{data.time || 'Not selected'}</p>
            </div>
            <div>
                <span className="text-surface-500">Duration</span>
                <p className="font-medium">{data.duration} minutes</p>
            </div>
            <div className="col-span-2">
                <span className="text-surface-500">Client</span>
                <p className="font-medium">{data.clientName || 'Not provided'}</p>
                <p className="text-surface-400 text-xs">{data.clientEmail}</p>
            </div>
            {data.notes && (
                <div className="col-span-2">
                    <span className="text-surface-500">Notes</span>
                    <p className="text-surface-300 text-xs">{data.notes}</p>
                </div>
            )}
        </div>
    </div>
);

export const BookingWizard: React.FC<BookingWizardProps> = ({
    steps,
    currentStep,
    bookingData,
    errors,
    isSubmitting,
    onStepChange,
    onDataChange,
    onSubmit,
    onCancel,
    className = '',
}) => {
    const currentStepConfig = steps[currentStep];
    const isFirstStep = currentStep === 0;
    const isLastStep = currentStep === steps.length - 1;
    const hasErrors = Object.values(errors).some(e => e);

    const handleNext = () => {
        if (!isLastStep) {
            onStepChange(currentStep + 1);
        } else {
            onSubmit();
        }
    };

    const handleBack = () => {
        if (!isFirstStep) {
            onStepChange(currentStep - 1);
        }
    };

    return (
        <div className={cn('bg-surface-900 rounded-xl p-6', className)}>
            {/* Step indicators */}
            <StepIndicator
                steps={steps}
                currentStep={currentStep}
                onStepClick={onStepChange}
            />

            {/* Step content */}
            <div className="min-h-[300px]">
                <StepHeader step={currentStepConfig} />

                {/* Dynamic step content based on step id */}
                <div className="max-w-md mx-auto">
                    {currentStepConfig.id === 'service' && (
                        <div className="space-y-3">
                            {['Portrait Session', 'Video Production', 'Commercial Shoot', 'Event Coverage'].map((type) => (
                                <button
                                    key={type}
                                    onClick={() => onDataChange({ sessionType: type })}
                                    className={cn(
                                        'w-full p-3 rounded-lg border-2 text-left transition-all',
                                        bookingData.sessionType === type
                                            ? 'border-brand-500 bg-brand-500/10'
                                            : 'border-surface-700 hover:border-surface-600'
                                    )}
                                >
                                    <div className="font-medium">{type}</div>
                                    <div className="text-xs text-surface-400">Starting from $150</div>
                                </button>
                            ))}
                            {errors.sessionType && (
                                <div className="text-red-400 text-sm">{errors.sessionType}</div>
                            )}
                        </div>
                    )}

                    {currentStepConfig.id === 'datetime' && (
                        <div className="space-y-4">
                            <FormField label="Date" error={errors.date} required>
                                <input
                                    type="date"
                                    value={bookingData.date}
                                    onChange={(e) => onDataChange({ date: e.target.value })}
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
                                />
                            </FormField>

                            <FormField label="Time" error={errors.time} required>
                                <select
                                    value={bookingData.time}
                                    onChange={(e) => onDataChange({ time: e.target.value })}
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
                                >
                                    <option value="">Select a time</option>
                                    {['09:00 AM', '10:00 AM', '11:00 AM', '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM'].map((t) => (
                                        <option key={t} value={t}>{t}</option>
                                    ))}
                                </select>
                            </FormField>

                            <FormField label="Duration" error={errors.duration}>
                                <div className="flex gap-2">
                                    {[30, 60, 90, 120].map((d) => (
                                        <button
                                            key={d}
                                            onClick={() => onDataChange({ duration: d })}
                                            className={cn(
                                                'flex-1 py-2 rounded-lg border transition-colors',
                                                bookingData.duration === d
                                                    ? 'border-brand-500 bg-brand-500/10'
                                                    : 'border-surface-700 hover:border-surface-600'
                                            )}
                                        >
                                            {d} min
                                        </button>
                                    ))}
                                </div>
                            </FormField>
                        </div>
                    )}

                    {currentStepConfig.id === 'details' && (
                        <div className="space-y-4">
                            <FormField label="Your Name" error={errors.clientName} required>
                                <input
                                    type="text"
                                    value={bookingData.clientName}
                                    onChange={(e) => onDataChange({ clientName: e.target.value })}
                                    placeholder="John Doe"
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
                                />
                            </FormField>

                            <FormField label="Email" error={errors.clientEmail} required>
                                <input
                                    type="email"
                                    value={bookingData.clientEmail}
                                    onChange={(e) => onDataChange({ clientEmail: e.target.value })}
                                    placeholder="john@example.com"
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none"
                                />
                            </FormField>

                            <FormField label="Additional Notes" error={errors.notes}>
                                <textarea
                                    value={bookingData.notes}
                                    onChange={(e) => onDataChange({ notes: e.target.value })}
                                    placeholder="Any special requests or requirements..."
                                    rows={3}
                                    className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:outline-none resize-none"
                                />
                            </FormField>
                        </div>
                    )}

                    {currentStepConfig.id === 'confirm' && (
                        <div className="space-y-4">
                            <BookingPreview data={bookingData} />

                            <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                                <div className="flex items-center gap-2 text-green-400 text-sm">
                                    <Check className="w-4 h-4" />
                                    <span>All details look correct? Click confirm to book.</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-surface-700">
                <button
                    onClick={onCancel}
                    className="px-4 py-2 text-surface-400 hover:text-white transition-colors"
                >
                    Cancel
                </button>

                <div className="flex items-center gap-3">
                    {!isFirstStep && (
                        <button
                            onClick={handleBack}
                            className="flex items-center gap-1 px-4 py-2 bg-surface-800 hover:bg-surface-700 rounded-lg transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                            Back
                        </button>
                    )}

                    <button
                        onClick={handleNext}
                        disabled={isSubmitting || hasErrors}
                        className={cn(
                            'flex items-center gap-1 px-6 py-2 rounded-lg font-medium transition-colors',
                            isLastStep
                                ? 'bg-green-600 hover:bg-green-700 text-white'
                                : 'bg-brand-500 hover:bg-brand-600 text-white',
                            (isSubmitting || hasErrors) && 'opacity-50 cursor-not-allowed'
                        )}
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Processing...
                            </>
                        ) : isLastStep ? (
                            <>
                                <Check className="w-4 h-4" />
                                Confirm Booking
                            </>
                        ) : (
                            <>
                                Next
                                <ChevronRight className="w-4 h-4" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

// Default wizard steps
export const DEFAULT_BOOKING_STEPS: WizardStep[] = [
    {
        id: 'service',
        title: 'Select Service',
        description: 'Choose the type of session you need',
        icon: <FileText className="w-5 h-5" />,
    },
    {
        id: 'datetime',
        title: 'Pick Date & Time',
        description: 'Select when you\'d like to book',
        icon: <Calendar className="w-5 h-5" />,
    },
    {
        id: 'details',
        title: 'Your Details',
        description: 'Tell us about yourself',
        icon: <User className="w-5 h-5" />,
    },
    {
        id: 'confirm',
        title: 'Confirm',
        description: 'Review and confirm your booking',
        icon: <Check className="w-5 h-5" />,
    },
];

// Hook for booking wizard state
export function useBookingWizard() {
    const [currentStep, setCurrentStep] = React.useState(0);
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [errors, setErrors] = React.useState<ValidationErrors>({});
    const [bookingData, setBookingData] = React.useState<BookingData>({
        sessionType: '',
        date: '',
        time: '',
        duration: 60,
        clientName: '',
        clientEmail: '',
        notes: '',
    });

    const updateData = React.useCallback((updates: Partial<BookingData>) => {
        setBookingData((prev) => ({ ...prev, ...updates }));
        // Clear related errors
        const keys = Object.keys(updates);
        setErrors((prev) => {
            const newErrors = { ...prev };
            keys.forEach((k) => delete newErrors[k]);
            return newErrors;
        });
    }, []);

    const validateStep = React.useCallback((stepId: string): boolean => {
        const newErrors: ValidationErrors = {};

        if (stepId === 'service' && !bookingData.sessionType) {
            newErrors.sessionType = 'Please select a session type';
        }

        if (stepId === 'datetime') {
            if (!bookingData.date) newErrors.date = 'Date is required';
            if (!bookingData.time) newErrors.time = 'Time is required';
        }

        if (stepId === 'details') {
            if (!bookingData.clientName) newErrors.clientName = 'Name is required';
            if (!bookingData.clientEmail) {
                newErrors.clientEmail = 'Email is required';
            } else if (!/\S+@\S+\.\S+/.test(bookingData.clientEmail)) {
                newErrors.clientEmail = 'Please enter a valid email';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    }, [bookingData]);

    const goToStep = React.useCallback((step: number) => {
        setCurrentStep(step);
    }, []);

    const submit = React.useCallback(async () => {
        setIsSubmitting(true);
        try {
            // Simulate API call
            await new Promise((resolve) => setTimeout(resolve, 1500));
            console.log('Booking submitted:', bookingData);
            return true;
        } catch (error) {
            return false;
        } finally {
            setIsSubmitting(false);
        }
    }, [bookingData]);

    const reset = React.useCallback(() => {
        setCurrentStep(0);
        setErrors({});
        setBookingData({
            sessionType: '',
            date: '',
            time: '',
            duration: 60,
            clientName: '',
            clientEmail: '',
            notes: '',
        });
    }, []);

    return {
        currentStep,
        bookingData,
        errors,
        isSubmitting,
        updateData,
        validateStep,
        goToStep,
        submit,
        reset,
    };
}
