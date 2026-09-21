import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Activity, Clock, Zap, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HeatmapCell {
  day: string;
  time: string;
  dispatches: number;
  settledAmount: number;
  responseRate: number;
}

export const CadenceHeatmap: React.FC = () => {
  const [activeMetric, setActiveMetric] = useState<'dispatches' | 'settlements'>('dispatches');
  const [hoveredCell, setHoveredCell] = useState<HeatmapCell | null>(null);

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const timeSlots = ['9:00 AM', '11:00 AM', '1:00 PM', '3:00 PM', '5:00 PM'];

  // Matrix data: 5 time slots x 6 days
  const cellData: Record<string, Record<string, { dispatches: number; settledAmount: number; responseRate: number }>> = {
    '9:00 AM': {
      Mon: { dispatches: 18, settledAmount: 6400, responseRate: 72 },
      Tue: { dispatches: 32, settledAmount: 14200, responseRate: 88 },
      Wed: { dispatches: 24, settledAmount: 9800, responseRate: 81 },
      Thu: { dispatches: 29, settledAmount: 12500, responseRate: 84 },
      Fri: { dispatches: 15, settledAmount: 5100, responseRate: 64 },
      Sat: { dispatches: 4, settledAmount: 1200, responseRate: 40 },
    },
    '11:00 AM': {
      Mon: { dispatches: 28, settledAmount: 11200, responseRate: 82 },
      Tue: { dispatches: 42, settledAmount: 21800, responseRate: 94 }, // Peak
      Wed: { dispatches: 36, settledAmount: 16400, responseRate: 89 },
      Thu: { dispatches: 38, settledAmount: 18100, responseRate: 91 },
      Fri: { dispatches: 22, settledAmount: 8900, responseRate: 75 },
      Sat: { dispatches: 6, settledAmount: 1900, responseRate: 45 },
    },
    '1:00 PM': {
      Mon: { dispatches: 12, settledAmount: 3800, responseRate: 58 },
      Tue: { dispatches: 19, settledAmount: 7600, responseRate: 68 },
      Wed: { dispatches: 16, settledAmount: 6200, responseRate: 65 },
      Thu: { dispatches: 21, settledAmount: 8400, responseRate: 70 },
      Fri: { dispatches: 14, settledAmount: 4900, responseRate: 60 },
      Sat: { dispatches: 3, settledAmount: 800, responseRate: 35 },
    },
    '3:00 PM': {
      Mon: { dispatches: 24, settledAmount: 9400, responseRate: 79 },
      Tue: { dispatches: 35, settledAmount: 15600, responseRate: 86 },
      Wed: { dispatches: 31, settledAmount: 13200, responseRate: 83 },
      Thu: { dispatches: 34, settledAmount: 14800, responseRate: 85 },
      Fri: { dispatches: 18, settledAmount: 6800, responseRate: 67 },
      Sat: { dispatches: 2, settledAmount: 500, responseRate: 30 },
    },
    '5:00 PM': {
      Mon: { dispatches: 14, settledAmount: 4600, responseRate: 61 },
      Tue: { dispatches: 22, settledAmount: 8900, responseRate: 74 },
      Wed: { dispatches: 19, settledAmount: 7200, responseRate: 71 },
      Thu: { dispatches: 25, settledAmount: 10400, responseRate: 76 },
      Fri: { dispatches: 9, settledAmount: 2700, responseRate: 52 },
      Sat: { dispatches: 1, settledAmount: 200, responseRate: 20 },
    },
  };

  // Helper to get color intensity based on value
  const getCellColorClass = (slot: string, day: string) => {
    const val = activeMetric === 'dispatches'
      ? cellData[slot]?.[day]?.dispatches || 0
      : cellData[slot]?.[day]?.settledAmount || 0;

    if (activeMetric === 'dispatches') {
      if (val >= 35) return 'bg-blue-500 shadow-sm shadow-blue-500/40 border-blue-300/40 text-white';
      if (val >= 25) return 'bg-blue-600/90 border-blue-400/30 text-white';
      if (val >= 15) return 'bg-blue-800/60 border-blue-500/20 text-blue-200';
      if (val >= 6) return 'bg-slate-800/80 border-slate-700/40 text-slate-300';
      return 'bg-[#0b0d13] border-white/[0.04] text-slate-500';
    } else {
      if (val >= 15000) return 'bg-blue-500 shadow-sm shadow-blue-500/40 border-blue-300/40 text-white';
      if (val >= 10000) return 'bg-blue-600/90 border-blue-400/30 text-white';
      if (val >= 5000) return 'bg-blue-800/60 border-blue-500/20 text-blue-200';
      if (val >= 2000) return 'bg-slate-800/80 border-slate-700/40 text-slate-300';
      return 'bg-[#0b0d13] border-white/[0.04] text-slate-500';
    }
  };

  return (
    <Card className="piano-black-card relative overflow-hidden flex flex-col justify-between">
      <CardHeader className="pb-3 border-b border-white/[0.06]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-400" />
                Cadence Engagement Heatmap
              </CardTitle>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/25">
                <Zap className="w-2.5 h-2.5" /> High Yield
              </span>
            </div>
            <CardDescription className="text-xs text-slate-400 mt-0.5">
              Optimal outreach windows correlated with debtor response & same-day settlement velocity
            </CardDescription>
          </div>

          {/* Metric Selector Tabs */}
          <div className="flex items-center gap-1 bg-[#0a0c10] p-1 rounded-lg border border-white/[0.08] self-start sm:self-auto">
            <button
              onClick={() => setActiveMetric('dispatches')}
              className={cn(
                'px-2.5 py-1 text-[11px] font-medium rounded-md transition-all',
                activeMetric === 'dispatches'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              Dispatches
            </button>
            <button
              onClick={() => setActiveMetric('settlements')}
              className={cn(
                'px-2.5 py-1 text-[11px] font-medium rounded-md transition-all',
                activeMetric === 'settlements'
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              Settled ($)
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 pb-4">
        {/* Heatmap Grid Container */}
        <div className="overflow-x-auto">
          <div className="min-w-[420px]">
            {/* Day Header Row */}
            <div className="grid grid-cols-7 gap-2 mb-2 items-center text-center">
              <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-500 text-left pl-1">
                Time
              </div>
              {days.map((day) => (
                <div
                  key={day}
                  className="text-[11px] font-semibold tracking-wide text-slate-400"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Time Slot Rows */}
            <div className="space-y-2">
              {timeSlots.map((slot) => (
                <div key={slot} className="grid grid-cols-7 gap-2 items-center">
                  {/* Row Label */}
                  <div className="text-[10px] font-medium text-slate-400 flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5 text-slate-500" />
                    <span>{slot}</span>
                  </div>

                  {/* Day Cells */}
                  {days.map((day) => {
                    const cell = cellData[slot]?.[day];
                    const isHovered =
                      hoveredCell?.day === day && hoveredCell?.time === slot;

                    return (
                      <div
                        key={`${slot}-${day}`}
                        onMouseEnter={() =>
                          setHoveredCell({
                            day,
                            time: slot,
                            dispatches: cell?.dispatches || 0,
                            settledAmount: cell?.settledAmount || 0,
                            responseRate: cell?.responseRate || 0,
                          })
                        }
                        onMouseLeave={() => setHoveredCell(null)}
                        className={cn(
                          'h-9 rounded-lg border transition-all duration-150 flex flex-col items-center justify-center cursor-pointer relative group',
                          getCellColorClass(slot, day),
                          isHovered && 'scale-105 ring-2 ring-blue-400/80 z-10 brightness-110'
                        )}
                      >
                        <span className="text-[11px] font-bold numeric-mono leading-none">
                          {activeMetric === 'dispatches'
                            ? cell?.dispatches
                            : `$${(cell?.settledAmount ? cell.settledAmount / 1000 : 0).toFixed(1)}k`}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Dynamic Cell Detail Card / Summary Bar */}
        <div className="mt-4 pt-3 border-t border-white/[0.06] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs">
          {hoveredCell ? (
            <div className="flex items-center gap-3 text-slate-300">
              <span className="font-semibold text-white">
                {hoveredCell.day} {hoveredCell.time}:
              </span>
              <span className="flex items-center gap-1 text-blue-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                {hoveredCell.dispatches} automated notices
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-white font-medium numeric-mono">
                ${hoveredCell.settledAmount.toLocaleString()} recovered
              </span>
              <span className="text-slate-400">|</span>
              <span className="text-emerald-400 font-semibold numeric-mono">
                {hoveredCell.responseRate}% engagement
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-400">
              <Info className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span>
                Peak cadence yield window: <strong className="text-white">Tuesday 11:00 AM</strong> (94% engagement rate, $21.8k settled)
              </span>
            </div>
          )}

          {/* Density Legend */}
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400 self-end sm:self-auto shrink-0">
            <span>Low</span>
            <div className="flex gap-1 items-center">
              <span className="w-3 h-3 rounded bg-[#0b0d13] border border-white/[0.04]" />
              <span className="w-3 h-3 rounded bg-slate-800 border border-slate-700/40" />
              <span className="w-3 h-3 rounded bg-blue-800/70 border border-blue-500/20" />
              <span className="w-3 h-3 rounded bg-blue-600 border border-blue-400/30" />
              <span className="w-3 h-3 rounded bg-blue-500 border border-blue-300/40" />
            </div>
            <span>High</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
