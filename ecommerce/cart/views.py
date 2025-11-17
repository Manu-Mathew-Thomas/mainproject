from django.shortcuts import render,redirect
from django.views import View
from shop.models import Product
from cart.models import Cart
import razorpay
from cart.forms import OrderForm



class AddtoCart(View):
    def get(self,request,i):
        p=Product.objects.get(id=i)
        u=request.user
        try:
            c=Cart.objects.get(user=u,product=p)
            c.quantity+=1
            c.save()
        except:
            c=Cart.objects.create(user=u,product=p,quantity=1)
            c.save()
        return redirect('cart:cartview')


class Cartview(View):
    def get(self,request):
        u=request.user
        c=Cart.objects.filter(user=u)
        total=0
        for i in c:
            total+=i.product.price*i.quantity

        context={'cart':c,'total':total}
        return render(request,'cart.html',context)

class Cartdecrement(View):
    def get(self,request,i):
        p=Product.objects.get(id=i)
        u=request.user
        try:
            c=Cart.objects.get(user=u,product=p)
            if(c.quantity>1):
                c.quantity-=1
                c.save()
            else:
                c.delete()
        except:
            pass
        return redirect('cart:cartview')

class Cartremove(View):
    def get(self,request,i):
        p = Product.objects.get(id=i)
        u = request.user
        try:
            c = Cart.objects.get(user=u, product=p)

            c.delete()
        except:
            pass
        return redirect('cart:cartview')

def checkstock(c):
    for i in c:
        if i.product.stock<i.quantity:
            return False
    return True


from django.contrib import messages


# class Checkout(View):
#
#     def get(self, request):
#         user = request.user
#         cart_qs = Cart.objects.filter(user=user)
#         in_stock = checkstock(cart_qs)
#
#         # OUT OF STOCK -> only message
#         if not in_stock:
#             context = {
#                 "stock": False,
#                 "stock_message": "Currently items not available, cant place order. Please try again later!!!",
#             }
#             return render(request, "checkout.html", context)
#
#         # IN STOCK -> show form
#         form_instance = OrderForm()
#         context = {
#             "stock": True,
#             "form": form_instance,
#         }
#         return render(request, "checkout.html", context)
#
#     def post(self, request):
#         user = request.user
#         cart_qs = Cart.objects.filter(user=user)
#
#         # safety check again
#         in_stock = checkstock(cart_qs)
#         if not in_stock:
#             context = {
#                 "stock": False,
#                 "stock_message": "Currently items not available, cant place order. Please try again later!!!",
#             }
#             return render(request, "checkout.html", context)
#
#         form_instance = OrderForm(request.POST)
#
#         if form_instance.is_valid():
#             # ---- create order object ----
#             order = form_instance.save(commit=False)
#             order.user = user
#
#             total = 0
#             for item in cart_qs:
#                 total += item.product.price * item.quantity
#
#             order.amount = total   # make sure your Order model has amount
#             order.save()
#             print("Order saved with id:", order.id)
#
#             # ---- payment handling ----
#             # IMPORTANT: use the same value as in your form choices
#             # if you used ('online', 'ONLINE'), the value is 'online' (lowercase)
#             if order.payment_method == "online":
#                 print("Payment method = online, creating Razorpay order")
#                 client = razorpay.Client(auth=("rzp_test_RfE1mblAOkoa3l", "xA3Wi17XvtuWrIviVYaOth2Z"))
#                 response_payment = client.order.create(dict(
#                     amount = total * 100,   # in paise
#                     currency = "INR",
#                     payment_capture = 1
#                 ))
#                 print("response_payment:", response_payment)
#
#                 return render(
#                     request,
#                     "payment.html",
#                     {"order": order, "payment": response_payment},
#                 )
#
#             # COD branch
#             print("Payment method = COD, no Razorpay")
#             messages.success(request, "Order placed successfully with Cash on Delivery.")
#             return render(request, "payment.html", {"order": order})
#
#         # ---- form not valid ----
#         print("Form errors:", form_instance.errors)
#         messages.error(request, "Please correct the errors below.")
#         return render(
#             request,
#             "checkout.html",
#             {"form": form_instance, "stock": True},
      #  )
import uuid
class Checkout(View):
    def post(self,request):
        form_instance=OrderForm(request.POST)
        if form_instance.is_valid():
            o=form_instance.save(commit=False)

            u = request.user
            o.user=u

            c = Cart.objects.filter(user=u)
            total=0
            for i in c:
                total+=i.product.price*i.quantity
            o.amount=total
            o.save()
            print("order saved with id:",o.id)

            if(o.payment_method=="online"):
                #razorpay client connection
                client=razorpay.Client(auth=('rzp_test_RfE1mblAOkoa3l','xA3Wi17XvtuWrIviVYaOth2Z'))
                print(client)
                #place order
                response_payment=client.order.create(dict(amount=total*100,currency='INR'))
                print(response_payment)
                id=response_payment['id']
                o.order_id=id
                o.save()
                context={'payment':response_payment}
                return render(request,'payment.html',context)
            else:
                # order
                o.is_ordered = True
                uid=uuid.uuid4().hex[:14]
                id='order_COD'+uid
                o.order_id=id
                o.save()
                for i in c:
                    items = OrderItem.objects.create(order=o, product=i.product, quantity=i.quantity)
                    items.save()
                    items.product.stock -= items.quantity
                    items.product.save()

                # cart deletion
                c.delete()
                return render(request,'payment.html',)


    def get(self,request):
        u=request.user
        c=Cart.objects.filter(user=u)
        in_stock=checkstock(c)
        if not in_stock:
            context={"stock":False,"stock_message":"Currently items not available,cant place order,Please try again later!!!"}
            return render(request,"checkout.html",context)

        form_instance=OrderForm()
        context={'form':form_instance, 'stock':True,}
        return render(request,'checkout.html',context)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.contrib.auth import login
from cart.models import Order,OrderItem
@method_decorator(csrf_exempt,name="dispatch")
class Payment_success(View):


    def post(self,request,i):
        u=User.objects.get(username=i)
        login(request,u)
        response=request.POST
        print(response)
        id=response['razorpay_order_id']
        print(id)

        #order
        order=Order.objects.get(order_id=id)
        order.is_ordered=True
        order.save()

        #order_items
        c=Cart.objects.filter(user=u)
        for i in c:
            o=OrderItem.objects.create(order=order,product=i.product,quantity=i.quantity)
            o.save()
            o.product.stock-=o.quantity
            o.product.save()

        #cart deletion
        c.delete()
        return render(request,'payment_success.html')


class Orders(View):
    def get(self,request):
        u=request.user
        o=Order.objects.filter(user=u,is_ordered=True)
        context={'orders':o}
        return render(request,'orders.html',context)

