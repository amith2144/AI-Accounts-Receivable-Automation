import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ReminderCadence, ReminderTone } from '@/types';
import { Clock, Eye, Check, Edit2 } from 'lucide-react';

interface CadenceRuleEditorProps {
  cadences: ReminderCadence[];
  onSaveRule: (cadence: ReminderCadence) => Promise<void>;
}

export const CadenceRuleEditor: React.FC<CadenceRuleEditorProps> = ({
  cadences,
  onSaveRule,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<ReminderCadence>>({});
  const [isSaving, setIsSaving] = useState(false);

  const startEdit = (c: ReminderCadence) => {
    setEditingId(c.id);
    setFormData({ ...c });
  };

  const handleSave = async () => {
    if (!editingId) return;
    setIsSaving(true);
    try {
      await onSaveRule(formData as ReminderCadence);
      setEditingId(null);
    } finally {
      setIsSaving(false);
    }
  };

  const sampleTokens = {
    customer_name: 'Acme Logistics Corp',
    invoice_number: 'INV-2026-089',
    balance_due: '$4,250.00',
    due_date: 'Sep 15, 2026',
  };

  const renderPreview = (text?: string) => {
    if (!text) return '';
    return text
      .replace(/\{\{\s*customer_name\s*\}\}/g, sampleTokens.customer_name)
      .replace(/\{\{\s*invoice_number\s*\}\}/g, sampleTokens.invoice_number)
      .replace(/\{\{\s*balance_due\s*\}\}/g, sampleTokens.balance_due)
      .replace(/\{\{\s*due_date\s*\}\}/g, sampleTokens.due_date);
  };

  const getToneBadge = (tone: ReminderTone) => {
    switch (tone) {
      case 'FRIENDLY':
        return <Badge variant="success">Friendly</Badge>;
      case 'STANDARD':
        return <Badge variant="default">Standard</Badge>;
      case 'FIRM':
        return <Badge variant="warning">Firm</Badge>;
      case 'URGENT':
        return <Badge variant="destructive">Urgent</Badge>;
      default:
        return <Badge variant="neutral">{tone}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {cadences.map((cadence) => {
        const isEditing = editingId === cadence.id;

        return (
          <Card key={cadence.id} className="glass-card overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-3 bg-[#0e1017]/60 border-b border-[#1e212f]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#1a1c27] border border-[#272b3c] flex items-center justify-center text-blue-400">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-semibold">{cadence.name}</CardTitle>
                    {getToneBadge(cadence.reminder_tone)}
                    {cadence.is_active ? (
                      <Badge variant="success" dot>Active</Badge>
                    ) : (
                      <Badge variant="outline">Disabled</Badge>
                    )}
                  </div>
                  <CardDescription className="text-[11px] mt-0.5">
                    Triggers {cadence.trigger_offset_days === 0
                      ? 'on the invoice payment due date'
                      : cadence.trigger_offset_days < 0
                      ? `${Math.abs(cadence.trigger_offset_days)} days before due date`
                      : `${cadence.trigger_offset_days} days past due date`}
                  </CardDescription>
                </div>
              </div>

              <div>
                {!isEditing ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => startEdit(cadence)}
                    className="text-xs"
                  >
                    <Edit2 className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    <span>Configure Rule</span>
                  </Button>
                ) : (
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setEditingId(null)} disabled={isSaving}>
                      Cancel
                    </Button>
                    <Button variant="emerald" size="sm" onClick={handleSave} isLoading={isSaving}>
                      <Check className="w-3.5 h-3.5 mr-1" />
                      <span>Save Rule</span>
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-4 pt-4">
              {isEditing ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <Input
                      label="Rule Name"
                      value={formData.name || ''}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                    <Input
                      label="Trigger Offset (Days relative to due date)"
                      type="number"
                      value={formData.trigger_offset_days ?? 0}
                      onChange={(e) => setFormData({ ...formData, trigger_offset_days: parseInt(e.target.value, 10) })}
                      helperText="Negative = before due date; 0 = on due date; Positive = overdue"
                    />
                    <Select
                      label="Outreach Tone"
                      value={formData.reminder_tone || 'STANDARD'}
                      onChange={(e) => setFormData({ ...formData, reminder_tone: e.target.value as ReminderTone })}
                      options={[
                        { value: 'FRIENDLY', label: 'Friendly (Pre-due reminder)' },
                        { value: 'STANDARD', label: 'Standard (Due date notice)' },
                        { value: 'FIRM', label: 'Firm (Overdue follow-up)' },
                        { value: 'URGENT', label: 'Urgent (Final delinquency notice)' },
                      ]}
                    />
                  </div>

                  <Input
                    label="Email Subject Template"
                    value={formData.email_subject_template || ''}
                    onChange={(e) => setFormData({ ...formData, email_subject_template: e.target.value })}
                  />

                  <Textarea
                    label="Email Body Template (Jinja2 / Variable Placeholders)"
                    value={formData.email_body_template || ''}
                    onChange={(e) => setFormData({ ...formData, email_body_template: e.target.value })}
                  />

                  {/* Dynamic Preview */}
                  <div className="p-3.5 rounded-lg bg-[#0e1017] border border-[#232634] space-y-1.5">
                    <div className="text-[11px] font-semibold text-blue-400 flex items-center gap-1.5">
                      <Eye className="w-3.5 h-3.5" />
                      <span>Live Rendered Email Preview (Using Sample Context)</span>
                    </div>
                    <div className="text-xs font-medium text-white">
                      Subject: {renderPreview(formData.email_subject_template)}
                    </div>
                    <div className="text-xs text-slate-300 whitespace-pre-line bg-[#141620] p-3 rounded border border-[#1e212f]">
                      {renderPreview(formData.email_body_template)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 font-medium">Subject Template:</span>
                    <p className="text-slate-200 mt-0.5 font-medium">{cadence.email_subject_template}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Sample Preview:</span>
                    <p className="text-slate-400 mt-0.5 italic">
                      "{renderPreview(cadence.email_subject_template)}"
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
