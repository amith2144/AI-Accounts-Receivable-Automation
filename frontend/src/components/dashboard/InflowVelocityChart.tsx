import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { TrendingUp, ArrowUpRight, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DataPoint {
  label: string;
  actual: number;
  projected?: number;
  isProjected?: boolean;
}

export const InflowVelocityChart: React.FC = () => {
  const [timeframe, setTimeframe] = useState<'monthly' | 'weekly'>('monthly');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const monthlyData: DataPoint[] = [
    { label: 'Apr', actual: 21500 },
    { label: 'May', actual: 28200 },
    { label: 'Jun', actual: 24800 },
    { label: 'Jul', actual: 36400 },
    { label: 'Aug', actual: 32100 },
    { label: 'Sep', actual: 44500 },
    { label: 'Oct (Est)', actual: 48900, isProjected: true },
  ];

  const weeklyData: DataPoint[] = [
    { label: 'W1', actual: 7200 },
    { label: 'W2', actual: 11400 },
    { label: 'W3', actual: 9800 },
    { label: 'W4', actual: 14500 },
    { label: 'W5', actual: 12200 },
    { label: 'W6', actual: 16800 },
    { label: 'W7 (Est)', actual: 18200, isProjected: true },
  ];

  const data = timeframe === 'monthly' ? monthlyData : weeklyData;

  // SVG dimensions
  const svgWidth = 600;
  const svgHeight = 190;
  const paddingX = 40;
  const paddingTop = 25;
  const paddingBottom = 30;

  const minVal = 0;
  const maxVal = 55000;

  // Calculate coordinates
  const points = data.map((d, i) => {
    const x = paddingX + (i / (data.length - 1)) * (svgWidth - paddingX * 2);
    const y =
      svgHeight -
      paddingBottom -
      ((d.actual - minVal) / (maxVal - minVal)) * (svgHeight - paddingTop - paddingBottom);
    return { x, y, ...d };
  });

  // Generate smooth cubic Bézier curve path
  const generateSmoothPath = (pts: typeof points) => {
    if (pts.length === 0) return '';
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i === 0 ? 0 : i - 1];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] || p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    return d;
  };

  const linePath = generateSmoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${
    svgHeight - paddingBottom
  } L ${points[0].x} ${svgHeight - paddingBottom} Z`;

  return (
    <Card className="piano-black-card rounded-2xl relative overflow-hidden flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 gap-3 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <span>Receivables Inflow Velocity & Forecast</span>
              </CardTitle>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-0.5">
                <ArrowUpRight className="w-3 h-3" /> +14.2% MoM
              </span>
            </div>
            <CardDescription className="text-xs text-slate-400 mt-1">
              Historical ledger inflows vs projected 30-day autonomous cash recovery
            </CardDescription>
          </div>

          {/* Timeframe selector */}
          <div className="flex items-center gap-1 p-0.5 rounded-lg bg-[#06070a] border border-white/[0.08]">
            <button
              onClick={() => setTimeframe('monthly')}
              className={cn(
                'px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors',
                timeframe === 'monthly'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              Monthly
            </button>
            <button
              onClick={() => setTimeframe('weekly')}
              className={cn(
                'px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors',
                timeframe === 'weekly'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              Weekly
            </button>
          </div>
        </CardHeader>

        <CardContent className="pt-4 space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl piano-black-subcard">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Current Run-Rate
              </div>
              <div className="text-lg font-bold text-white numeric-mono mt-0.5">
                $44,500.00
              </div>
            </div>
            <div className="p-3 rounded-xl piano-black-subcard">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Next Cycle Projection
              </div>
              <div className="text-lg font-bold text-blue-400 numeric-mono mt-0.5">
                $48,900.00
              </div>
            </div>
            <div className="p-3 rounded-xl piano-black-subcard">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Working Capital Yield
              </div>
              <div className="text-lg font-bold text-slate-200 numeric-mono mt-0.5">
                94.8%
              </div>
            </div>
          </div>

          {/* SVG Smooth Area Curve */}
          <div className="relative w-full h-[200px] select-none">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-full overflow-visible"
            >
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.28" />
                  <stop offset="85%" stopColor="#3b82f6" stopOpacity="0.02" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                </linearGradient>

                <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#2563eb" />
                  <stop offset="80%" stopColor="#3b82f6" />
                  <stop offset="100%" stopColor="#60a5fa" />
                </linearGradient>
              </defs>

              {/* Horizontal Gridlines */}
              {[15000, 30000, 45000].map((val) => {
                const y =
                  svgHeight -
                  paddingBottom -
                  ((val - minVal) / (maxVal - minVal)) *
                    (svgHeight - paddingTop - paddingBottom);
                return (
                  <g key={val}>
                    <line
                      x1={paddingX}
                      y1={y}
                      x2={svgWidth - paddingX}
                      y2={y}
                      stroke="rgba(255, 255, 255, 0.05)"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={paddingX - 8}
                      y={y + 3}
                      textAnchor="end"
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="JetBrains Mono, monospace"
                    >
                      ${val / 1000}k
                    </text>
                  </g>
                );
              })}

              {/* Gradient Area Fill */}
              <path d={areaPath} fill="url(#areaGradient)" />

              {/* Smooth Bézier Stroke */}
              <path
                d={linePath}
                fill="none"
                stroke="url(#lineGradient)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Interactive Points */}
              {points.map((p, i) => (
                <g key={i}>
                  {/* Subtle vertical indicator on hover */}
                  {hoveredIndex === i && (
                    <line
                      x1={p.x}
                      y1={paddingTop}
                      x2={p.x}
                      y2={svgHeight - paddingBottom}
                      stroke="rgba(59, 130, 246, 0.4)"
                      strokeWidth="1"
                      strokeDasharray="2 2"
                    />
                  )}

                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={hoveredIndex === i ? 5.5 : 3.5}
                    fill={p.isProjected ? '#1e293b' : '#3b82f6'}
                    stroke={p.isProjected ? '#60a5fa' : '#ffffff'}
                    strokeWidth="1.5"
                    className="transition-all duration-150 cursor-pointer"
                    onMouseEnter={() => setHoveredIndex(i)}
                    onMouseLeave={() => setHoveredIndex(null)}
                  />

                  {/* X Axis Label */}
                  <text
                    x={p.x}
                    y={svgHeight - 10}
                    textAnchor="middle"
                    fill={p.isProjected ? '#94a3b8' : '#64748b'}
                    fontSize="10"
                    fontWeight={p.isProjected ? '600' : '500'}
                  >
                    {p.label}
                  </text>
                </g>
              ))}
            </svg>

            {/* Hover Tooltip Popup */}
            {hoveredIndex !== null && (
              <div
                className="absolute z-30 px-3 py-1.5 rounded-lg bg-[#12141f] border border-white/[0.15] shadow-2xl pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2"
                style={{
                  left: `${(points[hoveredIndex].x / svgWidth) * 100}%`,
                  top: `${(points[hoveredIndex].y / svgHeight) * 100}%`,
                }}
              >
                <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <Calendar className="w-2.5 h-2.5" />
                  <span>{points[hoveredIndex].label}</span>
                  {points[hoveredIndex].isProjected && (
                    <span className="text-blue-400 font-semibold">(Forecast)</span>
                  )}
                </div>
                <div className="text-xs font-bold text-white numeric-mono mt-0.5">
                  ${points[hoveredIndex].actual.toLocaleString()}.00
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </div>
    </Card>
  );
};
