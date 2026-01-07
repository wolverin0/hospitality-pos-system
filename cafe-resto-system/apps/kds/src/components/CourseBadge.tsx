
import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface CourseBadgeProps {
  course: string;
  className?: string;
}

const getCourseColor = (course: string) => {
  const normalized = course.toUpperCase();
  switch (normalized) {
    case 'DRINKS': return 'bg-cyan-900/50 text-cyan-200 border-cyan-700';
    case 'APPETIZERS': return 'bg-orange-900/50 text-orange-200 border-orange-700';
    case 'SOUPS': return 'bg-amber-900/50 text-amber-200 border-amber-700';
    case 'SALADS': return 'bg-lime-900/50 text-lime-200 border-lime-700';
    case 'MAINS': return 'bg-indigo-900/50 text-indigo-200 border-indigo-700';
    case 'DESSERT': return 'bg-pink-900/50 text-pink-200 border-pink-700';
    case 'COFFEE': return 'bg-stone-700 text-stone-200 border-stone-500';
    default: return 'bg-gray-700 text-gray-200 border-gray-600';
  }
};

export const CourseBadge: React.FC<CourseBadgeProps> = ({ course, className }) => {
  const colorClass = getCourseColor(course);

  return (
    <span
      className={twMerge(
        'px-2 py-0.5 rounded text-xs font-semibold border uppercase tracking-wide',
        colorClass,
        className
      )}
    >
      {course}
    </span>
  );
};
