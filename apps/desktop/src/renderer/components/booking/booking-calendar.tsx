/**
 * BookingCalendar Component
 * Interactive calendar with availability slots and booking conflicts
 */

import React from 'react';
import {
    ChevronLeft,
    ChevronRight,
    Clock,
    X,
    AlertTriangle,
    Check,
    Calendar as CalendarIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Time slot interface
export interface TimeSlot {
    time: string;
    available: boolean;
    booked?: boolean;
    bookingId?: string;
    bookingTitle?: string;
}

// Day data interface
export interface DayData {
    date: Date;
    slots: TimeSlot[];
    isToday: boolean;
    isSelected: boolean;
    isPast: boolean;
    hasAvailability: boolean;
    hasConflict: boolean;
}

// Booking event for display
export interface BookingEvent {
    id: string;
    title: string;
    date: string;
    startTime: string;
    endTime: string;
    clientName: string;
    status: 'confirmed' | 'pending' | 'cancelled';
}

interface BookingCalendarProps {
    selectedDate: Date | null;
    onDateSelect: (date: Date) => void;
    onTimeSelect: (date: Date, time: string) => void;
    bookings: BookingEvent[];
    availableSlots?: string[]; // Default available times
    blockedDates?: string[];   // Dates that are fully blocked
    className?: string;
}

// Day names
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
];

// Default available time slots
const DEFAULT_SLOTS = [
    '09:00', '10:00', '11:00', '12:00',
    '14:00', '15:00', '16:00', '17:00',
];

// Format date as YYYY-MM-DD
const formatDateKey = (date: Date): string => {
    return date.toISOString().split('T')[0];
};

// Format time for display
const formatTime = (time: string): string => {
    const [hours, minutes] = time.split(':');
    const h = parseInt(hours);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hour12 = h % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
};

export const BookingCalendar: React.FC<BookingCalendarProps> = ({
    selectedDate,
    onDateSelect,
    onTimeSelect,
    bookings,
    availableSlots = DEFAULT_SLOTS,
    blockedDates = [],
    className = '',
}) => {
    const [currentMonth, setCurrentMonth] = React.useState(new Date());
    const [hoveredDate, setHoveredDate] = React.useState<Date | null>(null);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Get days in current month view
    const getDaysInMonth = (): DayData[] => {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();

        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startPadding = firstDay.getDay();
        const totalDays = lastDay.getDate();

        const days: DayData[] = [];

        // Previous month padding
        const prevMonth = new Date(year, month, 0);
        for (let i = startPadding - 1; i >= 0; i--) {
            const date = new Date(prevMonth);
            date.setDate(prevMonth.getDate() - i);
            days.push(createDayData(date, true));
        }

        // Current month days
        for (let i = 1; i <= totalDays; i++) {
            const date = new Date(year, month, i);
            days.push(createDayData(date, false));
        }

        // Next month padding
        const remaining = 42 - days.length; // 6 rows × 7 days
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i);
            days.push(createDayData(date, true));
        }

        return days;
    };

    // Create day data with availability info
    const createDayData = (date: Date, isOutsideMonth: boolean): DayData => {
        const dateKey = formatDateKey(date);
        const isPast = date < today;
        const isToday = dateKey === formatDateKey(today);
        const isSelected = selectedDate ? dateKey === formatDateKey(selectedDate) : false;
        const isBlocked = blockedDates.includes(dateKey);

        // Get bookings for this day
        const dayBookings = bookings.filter((b) => b.date === dateKey);
        const bookedTimes = dayBookings.map((b) => b.startTime);

        // Calculate available slots
        const slots: TimeSlot[] = availableSlots.map((time) => ({
            time,
            available: !isPast && !isBlocked && !bookedTimes.includes(time),
            booked: bookedTimes.includes(time),
            bookingId: dayBookings.find((b) => b.startTime === time)?.id,
            bookingTitle: dayBookings.find((b) => b.startTime === time)?.title,
        }));

        const hasAvailability = slots.some((s) => s.available);
        const hasConflict = dayBookings.some((b) => b.status === 'pending');

        return {
            date,
            slots,
            isToday,
            isSelected,
            isPast: isPast || isOutsideMonth,
            hasAvailability: !isOutsideMonth && hasAvailability,
            hasConflict,
        };
    };

    // Navigate months
    const prevMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
    };

    const nextMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
    };

    const goToToday = () => {
        setCurrentMonth(new Date());
        onDateSelect(new Date());
    };

    // Get slots for selected date
    const selectedDayData = selectedDate
        ? getDaysInMonth().find((d) => formatDateKey(d.date) === formatDateKey(selectedDate))
        : null;

    return (
        <div className={cn('bg-surface-900 rounded-xl p-4', className)}>
            {/* Calendar header */}
            <div className="flex items-center justify-between mb-4">
                <button
                    onClick={prevMonth}
                    className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
                >
                    <ChevronLeft className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold">
                        {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                    </h2>
                    <button
                        onClick={goToToday}
                        className="text-xs px-2 py-1 bg-surface-800 hover:bg-surface-700 rounded transition-colors"
                    >
                        Today
                    </button>
                </div>

                <button
                    onClick={nextMonth}
                    className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
                >
                    <ChevronRight className="w-5 h-5" />
                </button>
            </div>

            {/* Day headers */}
            <div className="grid grid-cols-7 gap-1 mb-2">
                {DAYS.map((day) => (
                    <div key={day} className="text-center text-xs font-medium text-surface-500 py-2">
                        {day}
                    </div>
                ))}
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
                {getDaysInMonth().map((day, index) => (
                    <button
                        key={index}
                        onClick={() => !day.isPast && day.hasAvailability && onDateSelect(day.date)}
                        onMouseEnter={() => setHoveredDate(day.date)}
                        onMouseLeave={() => setHoveredDate(null)}
                        disabled={day.isPast || !day.hasAvailability}
                        className={cn(
                            'relative aspect-square p-1 rounded-lg text-sm transition-all',
                            day.isSelected
                                ? 'bg-brand-500 text-white'
                                : day.isToday
                                    ? 'bg-brand-500/20 text-brand-400'
                                    : day.isPast
                                        ? 'text-surface-600 cursor-not-allowed'
                                        : day.hasAvailability
                                            ? 'hover:bg-surface-800 cursor-pointer'
                                            : 'text-surface-600 cursor-not-allowed'
                        )}
                    >
                        <span>{day.date.getDate()}</span>

                        {/* Availability indicator */}
                        {!day.isPast && day.hasAvailability && (
                            <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-green-500" />
                        )}

                        {/* Conflict indicator */}
                        {day.hasConflict && (
                            <div className="absolute top-1 right-1 w-2 h-2 rounded-full bg-yellow-500" />
                        )}
                    </button>
                ))}
            </div>

            {/* Time slots for selected date */}
            {selectedDate && selectedDayData && (
                <div className="mt-4 pt-4 border-t border-surface-700">
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-surface-400" />
                        Available times for {selectedDate.toLocaleDateString('en-US', {
                            weekday: 'long',
                            month: 'short',
                            day: 'numeric'
                        })}
                    </h3>

                    <div className="grid grid-cols-4 gap-2">
                        {selectedDayData.slots.map((slot) => (
                            <button
                                key={slot.time}
                                onClick={() => slot.available && onTimeSelect(selectedDate, slot.time)}
                                disabled={!slot.available}
                                className={cn(
                                    'py-2 px-3 rounded-lg text-sm font-medium transition-colors',
                                    slot.available
                                        ? 'bg-surface-800 hover:bg-brand-500 hover:text-white'
                                        : slot.booked
                                            ? 'bg-red-500/20 text-red-400 cursor-not-allowed'
                                            : 'bg-surface-800/50 text-surface-600 cursor-not-allowed'
                                )}
                                title={slot.bookingTitle || undefined}
                            >
                                {formatTime(slot.time)}
                                {slot.booked && <span className="ml-1 text-xs">(Booked)</span>}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Upcoming bookings */}
            {bookings.length > 0 && (
                <div className="mt-4 pt-4 border-t border-surface-700">
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                        <CalendarIcon className="w-4 h-4 text-surface-400" />
                        Upcoming Bookings
                    </h3>

                    <div className="space-y-2 max-h-40 overflow-y-auto">
                        {bookings
                            .filter((b) => b.status !== 'cancelled')
                            .slice(0, 5)
                            .map((booking) => (
                                <div
                                    key={booking.id}
                                    className="flex items-center justify-between p-2 bg-surface-800 rounded-lg text-sm"
                                >
                                    <div>
                                        <div className="font-medium">{booking.title}</div>
                                        <div className="text-xs text-surface-400">
                                            {booking.date} • {formatTime(booking.startTime)} - {formatTime(booking.endTime)}
                                        </div>
                                    </div>
                                    <span
                                        className={cn(
                                            'px-2 py-0.5 rounded text-xs',
                                            booking.status === 'confirmed'
                                                ? 'bg-green-500/20 text-green-400'
                                                : 'bg-yellow-500/20 text-yellow-400'
                                        )}
                                    >
                                        {booking.status}
                                    </span>
                                </div>
                            ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// Hook for calendar state
export function useBookingCalendar(initialBookings: BookingEvent[] = []) {
    const [selectedDate, setSelectedDate] = React.useState<Date | null>(null);
    const [selectedTime, setSelectedTime] = React.useState<string | null>(null);
    const [bookings, setBookings] = React.useState<BookingEvent[]>(initialBookings);

    const addBooking = React.useCallback((booking: BookingEvent) => {
        setBookings((prev) => [...prev, booking]);
    }, []);

    const cancelBooking = React.useCallback((bookingId: string) => {
        setBookings((prev) =>
            prev.map((b) =>
                b.id === bookingId ? { ...b, status: 'cancelled' as const } : b
            )
        );
    }, []);

    const confirmBooking = React.useCallback((bookingId: string) => {
        setBookings((prev) =>
            prev.map((b) =>
                b.id === bookingId ? { ...b, status: 'confirmed' as const } : b
            )
        );
    }, []);

    const checkConflict = React.useCallback((date: string, time: string): boolean => {
        return bookings.some(
            (b) => b.date === date && b.startTime === time && b.status !== 'cancelled'
        );
    }, [bookings]);

    return {
        selectedDate,
        selectedTime,
        bookings,
        setSelectedDate,
        setSelectedTime,
        addBooking,
        cancelBooking,
        confirmBooking,
        checkConflict,
    };
}
