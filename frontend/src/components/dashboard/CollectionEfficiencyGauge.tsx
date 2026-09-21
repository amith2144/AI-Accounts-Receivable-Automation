import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Target } from 'lucide-react';

export const CollectionEfficiencyGauge: React.FC = () => {
  // Concentric arc definitions
  // Circumference = 2 * PI * r
  // We use half or 220-degree arcs (from 160 to 380 deg or 180 to 0)
  // Let's use 240-degree open arcs (standard dashboard gauge style) or semicircular arcs
  const arcs = [
    {
      id: 'on_time',
      name: 'On-Time Settlement',
      percentage: 92,
      color: '#3b82f6', // Sapphire Blue
      trackColor: 'rgba(59, 130, 246, 0.12)',
      radius: 70,
      strokeWidth: 6,
    },
    {
      id: 'cadence_conv',
      name: 'Cadence Outreach Conv.',
      percentage: 84,
      color: '#2563eb', // Cobalt Blue
      trackColor: 'rgba(37, 99, 235, 0.12)',
      radius: 54,
      strokeWidth: 6,
    },
    {
      id: 'delinquent_res',
      name: 'Delinquency Resolution',
      percentage: 68,
      color: '#94a3b8', // Muted Cool Slate
      trackColor: 'rgba(148, 163, 184, 0.12)',
      radius: 38,
      strokeWidth: 6,
    },
  ];

  // SVG parameters
  const size = 200;
  const center = size / 2;

  // Render an open arc (e.g. 260 degrees from 140° to 400°)
  const startAngle = 140;
  const endAngle = 400;
  const totalAngle = endAngle - startAngle;

  const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: centerX + radius * Math.cos(angleInRadians),
      y: centerY + radius * Math.sin(angleInRadians),
    };
  };

  const describeArc = (x: number, y: number, radius: number, start: number, end: number) => {
    const startPt = polarToCartesian(x, y, radius, end);
    const endPt = polarToCartesian(x, y, radius, start);
    const largeArcFlag = end - start <= 180 ? '0' : '1';
    return ['M', startPt.x, startPt.y, 'A', radius, radius, 0, largeArcFlag, 0, endPt.x, endPt.y].join(' ');
  };

  return (
    <Card className="piano-black-card rounded-2xl relative overflow-hidden flex flex-col justify-between">
      <div>
        <CardHeader className="pb-2 border-b border-white/[0.06]">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Target className="w-4 h-4" />
              </div>
              <span>Collection Health & CEI</span>
            </CardTitle>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Optimal
            </span>
          </div>
          <CardDescription className="text-xs text-slate-400 mt-1">
            Tri-tier recovery velocity and portfolio conversion efficiency
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4 flex flex-col items-center">
          {/* Concentric Gauge SVG */}
          <div className="relative w-[190px] h-[170px] flex items-center justify-center">
            <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full">
              {arcs.map((arc) => {
                const filledAngle = startAngle + (arc.percentage / 100) * totalAngle;
                return (
                  <g key={arc.id}>
                    {/* Background Track */}
                    <path
                      d={describeArc(center, center, arc.radius, startAngle, endAngle)}
                      fill="none"
                      stroke={arc.trackColor}
                      strokeWidth={arc.strokeWidth}
                      strokeLinecap="round"
                    />

                    {/* Active Progress Arc */}
                    <path
                      d={describeArc(center, center, arc.radius, startAngle, filledAngle)}
                      fill="none"
                      stroke={arc.color}
                      strokeWidth={arc.strokeWidth}
                      strokeLinecap="round"
                      className="transition-all duration-700 ease-out"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Central Metric */}
            <div className="absolute top-[48%] left-1/2 -translate-x-1/2 -translate-y-1/2 text-center select-none">
              <div className="text-2xl font-bold text-white numeric-mono drop-shadow-md">
                88.4%
              </div>
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">
                CEI Index
              </div>
            </div>
          </div>

          {/* Structured Legend Breakdown */}
          <div className="w-full space-y-2 pt-2 border-t border-white/[0.06]">
            {arcs.map((arc) => (
              <div
                key={arc.id}
                className="flex items-center justify-between text-xs py-1 px-1.5 rounded-md hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: arc.color }}
                  />
                  <span className="text-slate-300 text-[11px] truncate">{arc.name}</span>
                </div>
                <span className="font-semibold text-white numeric-mono text-xs">
                  {arc.percentage}%
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </div>
    </Card>
  );
};
