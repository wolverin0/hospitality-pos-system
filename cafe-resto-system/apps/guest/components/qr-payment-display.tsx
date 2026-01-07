"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { Loader2, CheckCircle2, AlertCircle, RefreshCw, Smartphone } from "lucide-react";
import { cn } from "@/lib/utils";
import { PaymentIntent } from "@/lib/api";

interface QRPaymentDisplayProps {
  paymentIntent: PaymentIntent | null;
  status: "idle" | "creating" | "pending" | "completed" | "expired" | "failed";
  error: string | null;
  onRetry: () => void;
  className?: string;
}

export function QRPaymentDisplay({
  paymentIntent,
  status,
  error,
  onRetry,
  className,
}: QRPaymentDisplayProps) {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);

  useEffect(() => {
    if (paymentIntent?.qr_code) {
      QRCode.toDataURL(paymentIntent.qr_code, {
        width: 300,
        margin: 2,
        color: {
          dark: "#000000",
          light: "#ffffff",
        },
      })
        .then(setQrDataUrl)
        .catch((err) => console.error("QR Code generation error", err));
    }
  }, [paymentIntent?.qr_code]);

  return (
    <div className={cn("flex flex-col items-center justify-center space-y-6 p-6 rounded-xl border bg-card text-card-foreground shadow-sm w-full max-w-md mx-auto animate-in fade-in zoom-in duration-300", className)}>
      
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Pay at Table</h2>
        <p className="text-muted-foreground text-sm">
            Scan the QR code to pay instantly
        </p>
      </div>

      {/* Main Content Area */}
      <div className="relative flex items-center justify-center min-h-[300px] w-full bg-muted/20 rounded-lg border-2 border-dashed border-muted">
        
        {/* Loading State */}
        {(status === "creating" || (status === "pending" && !qrDataUrl)) && (
          <div className="flex flex-col items-center gap-4 animate-pulse">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="text-sm font-medium text-muted-foreground">Generating secure QR code...</p>
          </div>
        )}

        {/* Success State */}
        {status === "completed" && (
          <div className="flex flex-col items-center gap-4 text-green-500 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <CheckCircle2 className="h-20 w-20" />
            <div className="text-center">
              <h3 className="text-xl font-bold text-foreground">Payment Successful!</h3>
              <p className="text-sm text-muted-foreground mt-1">Thank you for dining with us.</p>
            </div>
          </div>
        )}

        {/* Error / Expired State */}
        {(status === "failed" || status === "expired" || error) && (
          <div className="flex flex-col items-center gap-4 text-destructive animate-in fade-in slide-in-from-bottom-4 duration-500">
            <AlertCircle className="h-16 w-16" />
            <div className="text-center px-4">
              <h3 className="text-lg font-bold text-foreground">
                {status === "expired" ? "QR Code Expired" : "Something went wrong"}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {error || "Please try generating a new code."}
              </p>
            </div>
            <button
              onClick={onRetry}
              className="flex items-center gap-2 px-4 py-2 mt-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>
          </div>
        )}

        {/* QR Display */}
        {status === "pending" && qrDataUrl && (
          <div className="flex flex-col items-center gap-4 w-full p-4 animate-in fade-in zoom-in duration-500">
            <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-1000"></div>
                <div className="relative bg-white p-4 rounded-lg shadow-xl">
                    <img src={qrDataUrl} alt="Payment QR Code" className="w-64 h-64 object-contain" />
                </div>
            </div>
            
            <div className="flex flex-col items-center gap-2 w-full mt-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Waiting for payment...</span>
                </div>
                
                {paymentIntent?.qr_expires_at && (
                   <p className="text-xs text-muted-foreground">
                     Expires at {new Date(paymentIntent.qr_expires_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                   </p>
                )}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {status === "pending" && (
        <div className="w-full space-y-3">
            <a 
                href={`mercadopago://qr?data=${encodeURIComponent(paymentIntent?.qr_code || '')}`}
                className="flex items-center justify-center gap-2 w-full py-3 bg-[#009EE3] hover:bg-[#008AD6] text-white rounded-lg font-semibold transition-transform active:scale-95 shadow-md"
            >
                <Smartphone className="h-5 w-5" />
                Scan with Mercado Pago
            </a>
        </div>
      )}
    </div>
  );
}
