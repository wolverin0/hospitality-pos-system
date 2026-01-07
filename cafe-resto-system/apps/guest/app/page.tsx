export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome
          </h1>
          <p className="text-muted-foreground">
            Scan QR code to order from your table
          </p>
        </div>

        <div className="space-y-4">
          <button className="w-full h-12 px-8 rounded-md bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
            Scan QR Code
          </button>
          <button className="w-full h-12 px-8 rounded-md bg-secondary text-secondary-foreground font-medium hover:bg-secondary/90 transition-colors">
            View Menu
          </button>
        </div>

        <div className="text-center text-sm text-muted-foreground">
          <p>Powered by Hospitality OS</p>
        </div>
      </div>
    </main>
  );
}
