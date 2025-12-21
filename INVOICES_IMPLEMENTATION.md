# Invoices Feature Implementation Guide

## Database Setup

1. **Run the SQL script** in Supabase SQL Editor:
   - File: `back/create_invoices_table.sql`
   - This creates the `invoices` table with all necessary fields

## Backend Endpoints (Already Added)

The following endpoints are now available:
- `GET /api/invoices` - Get all invoices
- `GET /api/invoices/{invoice_id}` - Get single invoice
- `POST /api/invoices/process` - Process invoice image (already exists)
- `PATCH /api/invoices/{invoice_id}` - Update invoice
- `DELETE /api/invoices/{invoice_id}` - Delete invoice

## Frontend Implementation

The InvoicesScreen needs to be completely rewritten to support:

1. **List View**: Show all saved invoices from database
2. **Multiple Upload**: Allow selecting multiple images at once
3. **Batch Processing**: Process all selected images
4. **Edit Screen**: Full editing capability for:
   - Total price
   - Currency
   - Vendor
   - Date
   - Invoice number
   - Items (add, edit, delete)

## Key Changes Needed

### Type Definitions
```typescript
type SavedInvoice = {
  id: string;
  image_data: string;
  total_price: number | null;
  currency: string;
  vendor: string | null;
  date: string | null;
  invoice_number: string | null;
  extracted_data: ExtractedInvoiceData | null;
  created_at: string;
  updated_at: string;
};
```

### State Management
- `invoices: SavedInvoice[]` - List of all invoices
- `selectedInvoices: string[]` - For batch operations
- `editingInvoice: SavedInvoice | null` - Currently editing invoice
- `uploadQueue: string[]` - Images waiting to be processed

### Main Functions Needed
1. `loadInvoices()` - Fetch all invoices from API
2. `handlePickMultipleImages()` - Select multiple images
3. `handleProcessMultiple()` - Process all selected images
4. `handleEditInvoice(invoice)` - Open edit screen
5. `handleSaveInvoice(invoice)` - Save edited invoice
6. `handleDeleteInvoice(id)` - Delete invoice

## Next Steps

1. Replace the entire `InvoicesScreen` component
2. Add invoice list view
3. Add edit invoice screen component
4. Add styles for new components

