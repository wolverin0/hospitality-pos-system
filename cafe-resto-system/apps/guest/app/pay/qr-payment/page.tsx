"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { QRPaymentDisplay } from "@/components/qr-payment-display";
import { useQrPayment } from "@/lib/use-qr-payment";
import { ArrowLeft, CreditCard, Loader2 } from "lucide-react";
import Link from "next/link";

function QRPaymentPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const orderId = searchParams.get("order_id");
  const tableSessionId = searchParams.get("table_session_id");
  const amount = searchParams.get("amount"); // Optional display

  if (!orderId || !tableSessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6 text-center">
        <h1 className="text-xl font-bold mb-2">Missing Information</h1>
        <p className="text-muted-foreground mb-6">We couldn't find your order details.</p>
        <Link href="/" className="text-primary hover:underline">Return to Home</Link>
      </div>
    );
  }

  const {
    paymentIntent,
    status,
    error,
    createIntent,
    tipAmount,
    setTipAmount
  } = useQrPayment({
    orderId,
    tableSessionId,
    initialTipAmount: 0,
    onSuccess: () => {
        // Delay redirect slightly to show success message
        setTimeout(() => {
            // Redirect to table session or success page
             router.push(`/table-session/${tableSessionId}?payment_success=true`);
        }, 3000);
    }
  });

  // Auto-create intent on mount
  useEffect(() => {
    createIntent();
  }, [createIntent]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Navbar / Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <Link href={`/table-session/${tableSessionId}`} className="mr-4 p-2 rounded-full hover:bg-accent">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2 font-semibold">
            <CreditCard className="h-5 w-5" />
            <span>Checkout</span>
          </div>
        </div>
      </header>

      <main className="flex-1 container max-w-lg py-8 px-4 mx-auto">
        <div className="space-y-6">
            {/* Amount Display */}
            {amount && (
                <div className="text-center mb-8">
                    <p className="text-sm text-muted-foreground uppercase tracking-widest font-medium">Total to Pay</p>
                    <h1 className="text-4xl font-extrabold mt-2 tracking-tight">${amount}</h1>
                </div>
            )}

            {/* Tip Selection - Only show if not completed */}
            {status !== "completed" && status !== "creating" && (
                <div className="bg-card border rounded-lg p-4 shadow-sm">
                    <label className="text-sm font-medium mb-3 block">Add a Tip?</label>
                    <div className="grid grid-cols-4 gap-2">
                        {[0, 10, 15, 20].map((pct) => (
                            <button
                                key={pct}
                                onClick={() => {
                                    setTipAmount(pct); 
                                    createIntent(pct); 
                                }}
                                className={`py-2 px-1 text-sm font-medium rounded-md transition-all ${
                                    tipAmount === pct 
                                    ? "bg-primary text-primary-foreground shadow-md scale-105" 
                                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                                }`}
                            >
                                {pct === 0 ? "No Tip" : `${pct}%`}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <QRPaymentDisplay
                paymentIntent={paymentIntent}
                status={status}
                error={error}
                onRetry={() => createIntent()}
            />
        </div>
      </main>
    </div>
  );
}

export default function QRPaymentPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="animate-spin" /></div>}>
            <QRPaymentPageContent />
        </Suspense>
    )
}
