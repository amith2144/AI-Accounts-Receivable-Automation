import React, { useState, useRef } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { invoiceService } from '@/services/invoiceService';
import { DocumentImportStatus } from '@/types';
import { Upload, FileText, AlertCircle, Sparkles } from 'lucide-react';

interface InvoiceUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExtractionSuccess: (extractedData: DocumentImportStatus) => void;
}

export const InvoiceUploadModal: React.FC<InvoiceUploadModalProps> = ({
  isOpen,
  onClose,
  onExtractionSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = () => {
    setFile(null);
    setIsUploading(false);
    setStatusMessage(null);
    setError(null);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelected = (selectedFile: File) => {
    setError(null);
    // 25MB max size validation
    if (selectedFile.size > 25 * 1024 * 1024) {
      setError('File exceeds 25MB maximum limit.');
      return;
    }

    const validMimes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!validMimes.includes(selectedFile.type)) {
      setError('Only PDF, PNG, and JPEG invoice documents are supported.');
      return;
    }

    setFile(selectedFile);
  };

  const pollExtractionStatus = async (documentId: string) => {
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds

    const check = async () => {
      attempts++;
      try {
        const res = await invoiceService.getImportStatus(documentId);
        if (res.extraction_status === 'SUCCESS' || res.extraction_status === 'PARTIAL_SUCCESS') {
          setStatusMessage('Extraction verified! Staging data for side-by-side operator review...');
          setTimeout(() => {
            resetState();
            onClose();
            onExtractionSuccess(res);
          }, 800);
          return;
        } else if (res.extraction_status === 'FAILED') {
          setError(res.error_message || 'Document OCR parsing failed.');
          setIsUploading(false);
          return;
        }

        if (attempts < maxAttempts) {
          setStatusMessage(`Extracting financial fields with PyMuPDF & OCR heuristic engine... (${attempts}s)`);
          setTimeout(check, 1000);
        } else {
          setError('Extraction task timed out. Check Celery worker status.');
          setIsUploading(false);
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Error verifying extraction status.');
        setIsUploading(false);
      }
    };

    check();
  };

  const handleStartUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setStatusMessage('Uploading document to MinIO / S3 storage bucket...');
    setError(null);

    try {
      const uploadRes = await invoiceService.uploadInvoiceDocument(file);
      setStatusMessage('Ingestion complete. Queued for optical character extraction...');
      pollExtractionStatus(uploadRes.document_id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to upload document.');
      setIsUploading(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={() => {
        if (!isUploading) {
          resetState();
          onClose();
        }
      }}
      title="Upload Invoice Document"
      description="Upload PDF or scanned image invoice for autonomous heuristic and OCR extraction"
      maxWidth="md"
    >
      <div className="space-y-4">
        {error && (
          <div className="p-3 rounded-md bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Drop Zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            file
              ? 'border-blue-500/60 bg-blue-950/20'
              : 'border-[#262a3c] hover:border-slate-500 bg-[#0c0d14]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileSelected(e.target.files[0]);
              }
            }}
          />

          <div className="mx-auto w-12 h-12 rounded-xl bg-[#1a1c29] border border-[#2a2f42] flex items-center justify-center text-blue-400 mb-3">
            <Upload className="w-5 h-5" />
          </div>

          {file ? (
            <div>
              <div className="text-sm font-semibold text-white flex items-center justify-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span>{file.name}</span>
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB • Ready for AI extraction
              </div>
            </div>
          ) : (
            <div>
              <div className="text-sm font-medium text-slate-200">
                Click or drag & drop invoice document here
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Supports PDF, PNG, and JPEG up to 25 MB
              </div>
            </div>
          )}
        </div>

        {/* Status Message & Extraction Progress */}
        {isUploading && (
          <div className="p-3.5 rounded-lg bg-[#141724] border border-[#23273c] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-blue-400 font-medium flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 animate-pulse text-blue-400" />
                <span>AI Ingestion Pipeline</span>
              </span>
              <span className="text-slate-400 text-[11px] animate-pulse">Processing...</span>
            </div>
            <p className="text-xs text-slate-300">{statusMessage}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1e212f]">
          <Button
            variant="ghost"
            size="sm"
            disabled={isUploading}
            onClick={() => {
              resetState();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!file || isUploading}
            isLoading={isUploading}
            onClick={handleStartUpload}
          >
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            <span>Process & Extract</span>
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
