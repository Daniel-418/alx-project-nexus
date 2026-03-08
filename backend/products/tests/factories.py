# type: ignore
import factory
import products.models as models


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Product

    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    name = factory.Faker("word")
    description = factory.Faker("text")


class OptionTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.OptionType

    option_type = factory.Faker("word")


class OptionValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.OptionValue

    value = factory.Faker("word")
    option_type = factory.SubFactory(OptionTypeFactory)


class VariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Variant

    product = factory.SubFactory(ProductFactory)
    sku = factory.Faker(
        "bothify", text="???-###-???", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)

    @factory.post_generation
    def option_values(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for option_value in extracted:
                self.option_values.add(option_value)

        else:
            self.option_values.add(OptionValueFactory())


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ProductImage

    variant = None
    product = factory.SubFactory(ProductFactory)
    image = factory.django.ImageField(color="blue", height=100, width=100)
    alt_text = factory.Faker("sentence")
    is_feature = False
    display_order = None

    class Params:
        for_variant = factory.Trait(
            product=None, variant=factory.SubFactory(VariantFactory)
        )
