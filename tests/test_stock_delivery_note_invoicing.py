from odoo.addons.link_it_foundation.tests.sale_order import SaleOrderTest


class StockDeliveryNoteInvoicingTest(SaleOrderTest):
    customer = None

    desk_combination_line = None
    customizable_desk_line = None
    right_corner_desk_line = None
    large_cabinet_line = None
    storage_box_line = None
    large_desk_line = None

    def create_delivery_note(self, **kwargs):
        vals = {
            'partner_id': self.customer.id,
            'partner_shipping_id': self.customer.id
        }

        vals.update(kwargs)

        return self.env['stock.delivery.note'].create(vals)

    def create_sales_order(self, lines, **kwargs):
        return super().create_sales_order(self.customer, lines, **kwargs)

    def setUp(self):
        super().setUp()

        self.customer = self.create_partner("Mario Rossi")

        try:
            self.desk_combination_line = self.prepare_sales_order_line(self.env.ref('product.product_product_3'), 1)
            self.customizable_desk_line = self.prepare_sales_order_line(self.env.ref('product.product_product_4'), 3)
            self.right_corner_desk_line = self.prepare_sales_order_line(self.env.ref('product.product_product_5'), 2)
            self.large_cabinet_line = self.prepare_sales_order_line(self.env.ref('product.product_product_6'), 11)
            self.storage_box_line = self.prepare_sales_order_line(self.env.ref('product.product_product_7'), 5)
            self.large_desk_line = self.prepare_sales_order_line(self.env.ref('product.product_product_8'), 1)

        except ValueError as exc:
            raise RuntimeError("It seems you're not using a database with"
                               " demonstration data loaded for this tests.") from exc

    # ⇒ "Ordine singolo: fatturazione completa"
    def test_complete_invoicing_single_so(self):
        #
        #     SO ┐         ┌ DdT
        #        └ Picking ┘
        #

        sales_order = self.create_sales_order([
            self.desk_combination_line,
            self.right_corner_desk_line,
            self.large_cabinet_line,
            self.large_desk_line
        ])
        sales_order.action_confirm()

        picking = sales_order.picking_ids
        self.assertEqual(len(picking), 1)

        picking.move_lines[0].quantity_done = 1
        picking.move_lines[1].quantity_done = 2
        picking.move_lines[2].quantity_done = 11
        picking.move_lines[3].quantity_done = 1

        result = picking.button_validate()
        self.assertIsNone(result)

        delivery_note = self.create_delivery_note()
        delivery_note.picking_ids = picking
        delivery_note.action_confirm()
        delivery_note.action_invoice()
        self.assertEqual(delivery_note.state, 'invoiced')

        invoice = sales_order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(sales_order.invoice_status, 'invoiced')

        #
        # Linea 1
        #
        order_line = sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Linea 2
        #
        order_line = sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 2)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 2)

        delivery_note_line = delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)

        #
        # Linea 3
        #
        order_line = sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 11)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 11)

        delivery_note_line = delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 11)

        invoice_line = invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 11)

        #
        # Linea 4
        #
        order_line = sales_order.order_line[3]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = delivery_note.line_ids[3]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = invoice.invoice_line_ids[3]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

    # ⇒ "Ordine singolo: fatturazione parziale"
    def test_partial_invoicing_single_so(self):
        #
        #     SO ┐         ┌ DdT
        #        ├ Picking ┘
        #        │
        #        └ Picking ┐
        #                  └ DdT
        #

        StockPicking = self.env['stock.picking']
        StockBackorderConfirmationWizard = self.env['stock.backorder.confirmation']

        sales_order = self.create_sales_order([
            self.customizable_desk_line,
            self.right_corner_desk_line,
            self.large_cabinet_line,
            self.storage_box_line
        ])
        sales_order.action_confirm()

        picking = sales_order.picking_ids
        self.assertEqual(len(picking), 1)

        picking.move_lines[0].quantity_done = 2  # 3
        picking.move_lines[1].quantity_done = 2
        picking.move_lines[2].quantity_done = 6  # 11
        picking.move_lines[3].quantity_done = 3  # 5

        wizard = StockBackorderConfirmationWizard.create({'pick_ids': [(4, picking.id)]})
        wizard.process()

        first_delivery_note = self.create_delivery_note()
        first_delivery_note.picking_ids = picking
        first_delivery_note.action_confirm()
        first_delivery_note.action_invoice()
        self.assertEqual(first_delivery_note.state, 'invoiced')

        first_invoice = sales_order.invoice_ids
        self.assertEqual(len(first_invoice), 1)
        self.assertEqual(sales_order.invoice_status, 'no')

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        backorder = StockPicking.search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1)

        backorder.move_lines[0].quantity_done = 1
        backorder.move_lines[1].quantity_done = 5
        backorder.move_lines[2].quantity_done = 2

        result = backorder.button_validate()
        self.assertIsNone(result)

        second_delivery_note = self.create_delivery_note()
        second_delivery_note.picking_ids = backorder
        second_delivery_note.action_confirm()

        #
        # Linea 1
        #
        order_line = sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 2)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 2)

        delivery_note_line = first_delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = first_invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)

        #
        # Linea 2
        #
        order_line = sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 2)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 2)

        delivery_note_line = first_delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = first_invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)

        #
        # Linea 3
        #
        order_line = sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 6)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 6)

        delivery_note_line = first_delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 6)

        invoice_line = first_invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 6)

        #
        # Linea 4
        #
        order_line = sales_order.order_line[3]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 3)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 3)

        delivery_note_line = first_delivery_note.line_ids[3]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 3)

        invoice_line = first_invoice.invoice_line_ids[3]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 3)

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        second_delivery_note.action_invoice()
        self.assertEqual(second_delivery_note.state, 'invoiced')

        second_invoice = sales_order.invoice_ids[0]
        self.assertEqual(len(second_invoice), 1)
        self.assertEqual(sales_order.invoice_status, 'invoiced')

        #
        # Linea 1
        #
        order_line = sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 3)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 1)

        delivery_note_line = second_delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = second_invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Linea 3
        #
        order_line = sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 11)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 5)

        delivery_note_line = second_delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 5)

        invoice_line = second_invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 5)

        #
        # Linea 4
        #
        order_line = sales_order.order_line[3]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 5)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 2)

        delivery_note_line = second_delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = second_invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)

    # ⇒ "Ordini multipli: fatturazione completa"
    def test_complete_invoicing_multiple_so(self):
        #
        #     SO ┐
        #        └ Picking ┐
        #                  ├ DdT
        #        ┌ Picking ┘
        #     SO ┘
        #

        first_sales_order = self.create_sales_order([
            self.desk_combination_line,
            self.customizable_desk_line,
            self.right_corner_desk_line
        ])
        first_sales_order.action_confirm()

        first_picking = first_sales_order.picking_ids
        self.assertEqual(len(first_picking), 1)

        first_picking.move_lines[0].quantity_done = 1
        first_picking.move_lines[1].quantity_done = 3
        first_picking.move_lines[2].quantity_done = 2

        result = first_picking.button_validate()
        self.assertIsNone(result)

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        second_sales_order = self.create_sales_order([
            self.large_cabinet_line,
            self.storage_box_line,
            self.large_desk_line
        ])
        second_sales_order.action_confirm()

        second_picking = second_sales_order.picking_ids
        self.assertEqual(len(second_picking), 1)

        second_picking.move_lines[0].quantity_done = 11
        second_picking.move_lines[1].quantity_done = 5
        second_picking.move_lines[2].quantity_done = 1

        result = second_picking.button_validate()
        self.assertIsNone(result)

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        pickings = first_picking | second_picking
        delivery_note = self.create_delivery_note()
        delivery_note.picking_ids = pickings
        delivery_note.action_confirm()
        delivery_note.action_invoice()
        self.assertEqual(delivery_note.state, 'invoiced')

        sales_orders = first_sales_order | second_sales_order
        invoice = sales_orders.mapped('invoice_ids')
        self.assertEqual(len(invoice), 1)
        self.assertEqual(first_sales_order.invoice_status, 'invoiced')
        self.assertEqual(second_sales_order.invoice_status, 'invoiced')

        #
        # Ordine 1 - Linea 1
        #
        order_line = first_sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Ordine 1 - Linea 2
        #
        order_line = first_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 3)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 3)

        delivery_note_line = delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 3)

        invoice_line = invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 3)

        #
        # Ordine 1 - Linea 3
        #
        order_line = first_sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 2)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 2)

        delivery_note_line = delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)

        #
        # Ordine 2 - Linea 1
        #
        order_line = second_sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 11)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 11)

        delivery_note_line = delivery_note.line_ids[3]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 11)

        invoice_line = invoice.invoice_line_ids[3]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 11)

        #
        # Ordine 2 - Linea 2
        #
        order_line = second_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 5)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 5)

        delivery_note_line = delivery_note.line_ids[4]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 5)

        invoice_line = invoice.invoice_line_ids[4]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 5)

        #
        # Ordine 2 - Linea 3
        #
        order_line = second_sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = delivery_note.line_ids[5]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = invoice.invoice_line_ids[5]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

    # ⇒ "Ordini multipli: fatturazione parziale"
    def test_partial_invoicing_multiple_so(self):
        #
        #        ┌ Picking ──────┐
        #     SO ┤               ├ DdT
        #        │     ┌ Picking ┘
        #        │  SO ┤
        #        │     └ Picking ┐
        #        │               ├ DdT
        #        └ Picking ──────┘
        #

        StockPicking = self.env['stock.picking']
        StockBackorderConfirmationWizard = self.env['stock.backorder.confirmation']

        first_sales_order = self.create_sales_order([
            self.desk_combination_line,
            self.right_corner_desk_line,
            self.large_desk_line
        ])
        first_sales_order.action_confirm()

        first_picking = first_sales_order.picking_ids
        self.assertEqual(len(first_picking), 1)

        first_picking.move_lines[0].quantity_done = 1
        first_picking.move_lines[1].quantity_done = 1  # 2
        first_picking.move_lines[2].quantity_done = 1

        wizard = StockBackorderConfirmationWizard.create({'pick_ids': [(4, first_picking.id)]})
        wizard.process()

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        second_sales_order = self.create_sales_order([
            self.customizable_desk_line,
            self.large_cabinet_line,
            self.storage_box_line
        ])
        second_sales_order.action_confirm()

        second_picking = second_sales_order.picking_ids
        self.assertEqual(len(second_picking), 1)

        second_picking.move_lines[0].quantity_done = 3
        second_picking.move_lines[1].quantity_done = 3  # 11
        second_picking.move_lines[2].quantity_done = 3  # 5

        wizard = StockBackorderConfirmationWizard.create({'pick_ids': [(4, second_picking.id)]})
        wizard.process()

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        pickings = first_picking | second_picking
        first_delivery_note = self.create_delivery_note()
        first_delivery_note.picking_ids = pickings
        first_delivery_note.action_confirm()
        first_delivery_note.action_invoice()
        self.assertEqual(first_delivery_note.state, 'invoiced')

        sales_orders = first_sales_order | second_sales_order
        first_invoice = sales_orders.mapped('invoice_ids')
        self.assertEqual(len(first_invoice), 1)
        self.assertEqual(first_sales_order.invoice_status, 'no')
        self.assertEqual(second_sales_order.invoice_status, 'no')

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        first_backorder = StockPicking.search([('backorder_id', '=', first_picking.id)])
        self.assertEqual(len(first_backorder), 1)

        first_backorder.move_lines[0].quantity_done = 1

        result = first_backorder.button_validate()
        self.assertIsNone(result)

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        second_backorder = StockPicking.search([('backorder_id', '=', second_picking.id)])
        self.assertEqual(len(second_backorder), 1)

        second_backorder.move_lines[0].quantity_done = 8
        second_backorder.move_lines[1].quantity_done = 2

        result = second_backorder.button_validate()
        self.assertIsNone(result)

        backorders = first_backorder | second_backorder
        second_delivery_note = self.create_delivery_note()
        second_delivery_note.picking_ids = backorders
        second_delivery_note.action_confirm()

        #
        # Ordine 1 - Linea 1
        #
        order_line = first_sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = first_delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = first_invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Ordine 1 - Linea 2
        #
        order_line = first_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 1)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 1)

        delivery_note_line = first_delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = first_invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Ordine 1 - Linea 3
        #
        order_line = first_sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 1)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 1)

        delivery_note_line = first_delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = first_invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Ordine 2 - Linea 1
        #
        order_line = second_sales_order.order_line[0]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 3)

        move = order_line.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity_done, 3)

        delivery_note_line = first_delivery_note.line_ids[3]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 3)

        invoice_line = first_invoice.invoice_line_ids[3]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 3)

        #
        # Ordine 2 - Linea 2
        #
        order_line = second_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 3)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 3)

        delivery_note_line = first_delivery_note.line_ids[4]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 3)

        invoice_line = first_invoice.invoice_line_ids[4]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 3)

        #
        # Ordine 2 - Linea 3
        #
        order_line = second_sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'to invoice')
        self.assertEqual(order_line.qty_invoiced, 3)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[0].quantity_done, 3)

        delivery_note_line = first_delivery_note.line_ids[5]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 3)

        invoice_line = first_invoice.invoice_line_ids[5]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 3)

        #
        # =      =  -  =    = - =    =  -  =      =
        #

        second_delivery_note.action_invoice()
        self.assertEqual(second_delivery_note.state, 'invoiced')

        second_invoice = sales_orders.mapped('invoice_ids')[1]
        self.assertEqual(len(second_invoice), 1)
        self.assertEqual(first_sales_order.invoice_status, 'invoiced')
        self.assertEqual(second_sales_order.invoice_status, 'invoiced')

        #
        # Ordine 1 - Linea 2
        #
        order_line = first_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 2)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 1)

        delivery_note_line = second_delivery_note.line_ids[0]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 1)

        invoice_line = second_invoice.invoice_line_ids[0]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 1)

        #
        # Ordine 2 - Linea 2
        #
        order_line = second_sales_order.order_line[1]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 11)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 8)

        delivery_note_line = second_delivery_note.line_ids[1]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 8)

        invoice_line = second_invoice.invoice_line_ids[1]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 8)

        #
        # Ordine 2 - Linea 3
        #
        order_line = second_sales_order.order_line[2]
        self.assertEqual(order_line.invoice_status, 'invoiced')
        self.assertEqual(order_line.qty_invoiced, 5)

        moves = order_line.move_ids
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves[1].quantity_done, 2)

        delivery_note_line = second_delivery_note.line_ids[2]
        self.assertEqual(delivery_note_line.sale_line_id, order_line)
        self.assertEqual(delivery_note_line.product_qty, 2)

        invoice_line = second_invoice.invoice_line_ids[2]
        self.assertEqual(invoice_line.sale_line_ids, order_line)
        self.assertEqual(invoice_line.quantity, 2)