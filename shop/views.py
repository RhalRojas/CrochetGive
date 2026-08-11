from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Product, Order, OrderItem
from .utils import calculate_donation_split, get_total_donated, invalidate_total_donated


def product_list(request):
    products = Product.objects.all()
    donated = get_total_donated()
    return render(request, "shop/product_list.html", {"products": products, "donated": donated})


def checkout(request):
    if request.method == "POST":
        order_total = Decimal("0.00")
        items_to_create = []

        for product in Product.objects.all():
            qty_str = request.POST.get(f"qty_{product.id}", "0")
            try:
                qty = int(qty_str)
            except ValueError:
                qty = 0

            if qty > product.stock:
                messages.error(request, f"Only {product.stock} left of {product.name}.")
                return redirect("product_list")

            if qty > 0:
                order_total += product.price * qty
                items_to_create.append((product, qty))

        if not items_to_create:
            messages.error(request, "Please select at least one item.")
            return redirect("product_list")

        donation_amount, seller_amount = calculate_donation_split(order_total)

        order = Order.objects.create(
            total_amount=order_total,
            donation_amount=donation_amount,
            seller_amount=seller_amount,
        )

        for product, qty in items_to_create:
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=qty,
                price_at_purchase=product.price,
            )
            product.stock -= qty
            product.save()

        invalidate_total_donated()

        return render(request, "shop/order_confirmation.html", {"order": order})

    return redirect("product_list")
