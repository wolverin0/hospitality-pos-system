// User Roles
export enum UserRole {
  ADMIN = "admin",
  MANAGER = "manager",
  WAITER = "waiter",
  CASHIER = "cashier",
  KITCHEN = "kitchen",
  EXPO = "expo",
}

// Draft Status
export enum DraftStatus {
  OPEN = "OPEN",
  SUBMITTED = "SUBMITTED",
  UPDATED = "UPDATED",
  IN_REVIEW = "IN_REVIEW",
  CONFIRMED = "CONFIRMED",
  REJECTED = "REJECTED",
  EXPIRED = "EXPIRED",
}

// Course Types
export enum Course {
  DRINKS = "DRINKS",
  APPETIZERS = "APPETIZERS",
  MAINS = "MAINS",
  DESSERT = "DESSERT",
}

// Station Types
export enum Station {
  BAR = "BAR",
  KITCHEN = "KITCHEN",
}

// Payment Methods
export enum PaymentMethod {
  CASH = "cash",
  EXTERNAL_TERMINAL = "external_terminal",
  QR = "qr",
}

// Payment Status
export enum PaymentStatus {
  PENDING = "PENDING",
  AUTHORIZED = "AUTHORIZED",
  PAID = "PAID",
  FAILED = "FAILED",
  REFUNDED = "REFUNDED",
}

// Stock Movement Types
export enum StockMovementType {
  RECEIVE = "RECEIVE",
  SELL = "SELL",
  TRANSFER_OUT = "TRANSFER_OUT",
  TRANSFER_IN = "TRANSFER_IN",
  ADJUSTMENT = "ADJUSTMENT",
}

// Transfer Status
export enum TransferStatus {
  CREATED = "CREATED",
  IN_TRANSIT = "IN_TRANSIT",
  RECEIVED = "RECEIVED",
}
