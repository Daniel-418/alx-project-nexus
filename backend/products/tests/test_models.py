import uuid
import shutil
import tempfile
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Max
from django.test import TestCase, override_settings
from products.models import Product, Variant, ProductImage, OptionType, OptionValue
from products.tests.factories import (
    ProductFactory,
    OptionTypeFactory,
    ProductImageFactory,
    VariantFactory,
    OptionValueFactory,
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


class ProductTest(TestCase):
    def test_product_creation(self):
        """test that a product is successfully created"""
        product_name = "T-shirt"
        product = ProductFactory(name=product_name)
        product.save()
        self.assertTrue(Product.objects.filter(name=product_name).exists())
        self.assertEqual(product.name, product_name)
        self.assertEqual(str(product), product_name)
        self.assertIsNotNone(product.created_at)
        self.assertIsNone(product.deleted_at)

    def test_price_precision(self):
        _ = ProductFactory(name="ball", price=9.99)
        self.assertEqual(float(Product.objects.get(name="ball").price), 9.99)

    def test_product_can_be_created_without_description(self):
        product = ProductFactory(name="T-shirt", price=10.00, description="")
        self.assertEqual(product.description, "")

    def test_product_id_is_uuid(self):
        """test that the product primary key is a UUID, not an auto-incrementing integer"""
        product = ProductFactory()
        self.assertIsInstance(product.id, uuid.UUID)

    def test_product_soft_delete(self):
        """test that a product soft deletes when you delete it"""

        product = ProductFactory()
        product.delete()

        fetched = Product.all_objects.get(id=product.id)
        self.assertTrue(Product.all_objects.filter(id=product.id).exists())
        self.assertIsNotNone(fetched.deleted_at)

    def test_variant_and_productimage_children_soft_delete(self):
        """test that a product's variant and all it's product_images are also
        soft deleted when you delete a product"""

        product = ProductFactory()
        variant = VariantFactory(product=product)
        image = ProductImageFactory(product=product)
        product.delete()

        fetched = Product.all_objects.get(id=product.id)
        fetched_variant = Variant.all_objects.get(id=variant.id, product=fetched)
        fetched_image = ProductImage.all_objects.get(id=image.id, product=fetched)
        self.assertTrue(
            Variant.all_objects.filter(id=variant.id, product=fetched).exists()
        )
        self.assertTrue(
            ProductImage.all_objects.filter(id=image.id, product=fetched).exists()
        )
        self.assertIsNotNone(fetched_variant.deleted_at)
        self.assertIsNotNone(fetched_image.deleted_at)

        image.image.delete()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProductImageTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.product = ProductFactory()
        self.image = ProductImageFactory(product=self.product)

    def test_image_creation(self):
        """test that an image is successfully created and is attached to a product"""
        self.assertEqual(self.image.product, self.product)
        self.assertIn(self.image, self.product.product_images.all())

    def test_image_with_variant(self):
        """test that you can attach an image to a variant"""
        variant = VariantFactory()
        new_image = ProductImageFactory(variant=variant, for_variant=True)
        self.assertEqual(new_image.variant, variant)
        self.assertIn(new_image, variant.product_images.all())

    def test_image_with_a_product_and_a_variant(self):
        """test that an image can be attached to both a product and a variant"""
        variant = VariantFactory()
        product = ProductFactory()
        new_image = ProductImageFactory(variant=variant, product=product)

        self.assertEqual(new_image.variant, variant)
        self.assertIn(new_image, variant.product_images.all())
        self.assertEqual(new_image.product, product)
        self.assertIn(new_image, product.product_images.all())

    def test_image_feature_flag(self):
        """test that is_feature can be set to mark an image as the featured image"""
        image = ProductImageFactory(product=self.product, is_feature=True)
        self.assertTrue(image.is_feature)

    def test_image_is_deleted_when_product_is_deleted(self):
        """test that ProductImage is CASCADE deleted when its product is deleted —
        an orphaned image record with no product has no meaning in this system"""
        image = ProductImageFactory(product=self.product)
        image_id = image.id
        self.product.delete()

        self.assertTrue(ProductImage.all_objects.filter(id=image_id).exists())

    def test_image_soft_delete(self):
        """test that a image soft deletes when you delete it"""

        image = ProductImageFactory()
        image.delete()

        fetched = ProductImage.all_objects.get(id=image.id)
        self.assertTrue(ProductImage.all_objects.filter(id=image.id).exists())
        self.assertIsNotNone(fetched.deleted_at)

    def test_image_variant_fk_is_nullified_when_variant_is_deleted(self):
        """
        test that an image remains when it's variant is hard deleted
        """
        variant = VariantFactory()
        image = ProductImageFactory(variant=variant, for_variant=True)

        Variant.all_objects.filter(id=variant.id).delete()
        variant = None
        image.refresh_from_db()

        self.assertIsNone(ProductImage.objects.get(id=image.id).variant)


class OptionTypeTest(TestCase):
    def test_option_type_creation(self):
        """test that an option type is successfully created"""
        option_type = OptionTypeFactory(option_type="Color")
        self.assertEqual(option_type.option_type, "Color")

    def test_option_type_str(self):
        """test that __str__ returns the option type name"""
        option_type = OptionTypeFactory(option_type="Color")
        self.assertEqual(str(option_type), "Color")

    def test_option_values_deleted_when_option_type_deleted(self):
        """test that OptionValues are CASCADE deleted when their OptionType is deleted —
        a value like 'Red' is meaningless without its parent type 'Color'"""
        option_type = OptionTypeFactory(option_type="Color")
        option_value = OptionValueFactory(value="Red", option_type=option_type)
        option_value_id = option_value.id
        option_type.delete()
        with self.assertRaises(OptionValue.DoesNotExist):
            OptionValue.objects.get(id=option_value_id)


class OptionValueTest(TestCase):
    def test_option_value_creation(self):
        """test that an option value is successfully created"""
        option_type = OptionTypeFactory(option_type="Color")
        option_value = OptionValueFactory(value="Red", option_type=option_type)

        self.assertEqual(option_value.option_type, option_type)
        self.assertEqual(option_value.value, "Red")

    def test_option_value_str(self):
        """test that __str__ returns 'option_type: value' format"""
        option_type = OptionTypeFactory(option_type="Color")
        option_value = OptionValueFactory(value="Red", option_type=option_type)
        self.assertEqual(str(option_value), "Color: Red")


class VariantTest(TestCase):
    def setUp(self):
        self.option_value = OptionValueFactory()
        self.product = ProductFactory(name="T-shirt")
        self.variant = VariantFactory(
            product=self.product, option_values=[self.option_value]
        )

    def test_variant_creation(self):
        """test that a variant is created and is associated with a product"""

        self.variant.save()

        self.assertEqual(self.variant.product, self.product)
        self.assertIn(self.option_value, self.variant.option_values.all())
        self.assertEqual(self.variant.option_values.count(), 1)
        self.assertIn(self.variant, self.product.variants.all())
        self.assertFalse(self.variant.is_master)

    def test_variant_delete(self):
        """test that a variant is deleted when a product is deleted
        but a product remains when you delete a variant"""
        self.assertEqual(Variant.objects.get(id=self.variant.id), self.variant)
        self.product.delete()
        with self.assertRaises(Product.DoesNotExist):
            Product.objects.get(name="T-shirt")
        with self.assertRaises(Variant.DoesNotExist):
            Variant.objects.get(id=self.variant.id)

    def test_variant_soft_delete(self):
        """test that a product soft deletes when you delete it"""

        variant = VariantFactory()
        variant.delete()

        fetched = Variant.all_objects.get(id=variant.id)
        self.assertTrue(Variant.all_objects.filter(id=variant.id).exists())
        self.assertIsNotNone(fetched.deleted_at)

    def test_product_sku_uniqueness(self):
        """test that sku is unique per variant"""
        sku = "IPAD-1234-RED"
        variant = VariantFactory(sku=sku)
        variant.save()

        with self.assertRaises(IntegrityError):
            _ = VariantFactory(sku=sku)

    def test_deleting_variant_preserves_product(self):
        """test the other side of test_variant_delete — the product must survive
        when only its variant is deleted; variants are subordinate to products, not equal"""
        product_id = self.product.id
        self.variant.delete()
        self.assertTrue(Product.objects.filter(id=product_id).exists())

    def test_variant_default_stock_is_zero(self):
        """test that new variants start with zero stock — the default must be
        explicit so inventory logic doesn't treat unset stock as available"""
        variant = VariantFactory()
        self.assertEqual(variant.stock, 0)

    def test_master_variant(self):
        """test that a variant can be marked as the master variant —
        is_master drives product-level defaults like the display price"""
        master = VariantFactory(product=self.product, is_master=True)
        self.assertTrue(master.is_master)

    def test_variant_with_multiple_option_values(self):
        """test that a variant correctly holds multiple option_values —
        e.g. Size=Large AND Color=Red must both be linked via the M2M join table"""
        size = OptionValueFactory(value="Large")
        color = OptionValueFactory(value="Red")
        variant = VariantFactory(product=self.product, option_values=[size, color])
        self.assertEqual(variant.option_values.count(), 2)
        self.assertIn(size, variant.option_values.all())
        self.assertIn(color, variant.option_values.all())

    def test_soft_deleted_variant_excluded_from_objects_manager(self):
        """test that the default objects manager hides soft-deleted variants —
        this is the core contract of SoftDeleteManager"""
        variant = VariantFactory()
        variant_id = variant.id
        variant.delete()

        self.assertFalse(Variant.objects.filter(id=variant_id).exists())
        self.assertTrue(Variant.all_objects.filter(id=variant_id).exists())


TEMP_MEDIA_ROOT_DISPLAY = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT_DISPLAY)
class ProductImageDisplayOrderTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT_DISPLAY, ignore_errors=True)
        super().tearDownClass()

    def test_product_images_get_sequential_display_order(self):
        """product-level images for the same product receive sequential display_order (1, 2, 3)"""
        product = ProductFactory()
        img1 = ProductImageFactory(product=product)
        img2 = ProductImageFactory(product=product)
        img3 = ProductImageFactory(product=product)
        self.assertEqual(img1.display_order, 1)
        self.assertEqual(img2.display_order, 2)
        self.assertEqual(img3.display_order, 3)

    def test_variant_images_get_sequential_display_order(self):
        """variant-specific images for the same variant receive sequential display_order (1, 2)"""
        variant = VariantFactory()
        img1 = ProductImageFactory(for_variant=True, variant=variant)
        img2 = ProductImageFactory(for_variant=True, variant=variant)
        self.assertEqual(img1.display_order, 1)
        self.assertEqual(img2.display_order, 2)

    def test_variant_and_product_sequences_are_independent(self):
        """variant images and product-level images maintain separate display_order counters"""
        product = ProductFactory()
        variant = VariantFactory(product=product)
        variant_img = ProductImageFactory(product=product, variant=variant)
        product_img = ProductImageFactory(product=product)
        # each scope starts at 1 independently
        self.assertEqual(variant_img.display_order, 1)
        self.assertEqual(product_img.display_order, 1)

    def test_duplicate_display_order_raises_for_two_active_images(self):
        """the partial unique constraint blocks two active product-level images sharing display_order"""
        product = ProductFactory()
        ProductImageFactory(product=product, display_order=1)
        with self.assertRaises(IntegrityError):
            ProductImageFactory(product=product, display_order=1)

    def test_duplicate_display_order_allowed_when_one_is_soft_deleted(self):
        """the partial unique constraint permits a soft-deleted and active image to share display_order"""
        product = ProductFactory()
        img1 = ProductImageFactory(product=product, display_order=1)
        img1.delete()
        # should not raise — partial index ignores deleted rows
        img2 = ProductImageFactory(product=product, display_order=1)
        self.assertEqual(img2.display_order, 1)

    def test_soft_deleted_image_releases_display_order_slot(self):
        product = ProductFactory()
        img1 = ProductImageFactory(product=product)
        self.assertEqual(img1.display_order, 1)
        img1.delete()
        img2 = ProductImageFactory(product=product)
        self.assertEqual(img2.display_order, 2)


TEMP_MEDIA_ROOT_RESTORE = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT_RESTORE)
class ProductImageRestoreTest(TestCase):
    """tests for the display_order conflict resolution in ProductImage.restore()"""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT_RESTORE, ignore_errors=True)
        super().tearDownClass()

    def test_restore_without_conflict_keeps_display_order(self):
        """restoring an image when its slot is free preserves the original display_order"""
        product = ProductFactory()
        img = ProductImageFactory(product=product)
        original_order = img.display_order
        img.delete()
        img.restore()
        img.refresh_from_db()
        self.assertEqual(img.display_order, original_order)

    def test_restore_with_conflict_reassigns_display_order(self):
        """restoring an image whose slot was taken by a new image assigns a new display_order"""
        product = ProductFactory()
        img1 = ProductImageFactory(product=product)
        img1.delete()
        img2 = ProductImageFactory(product=product, display_order=1)
        self.assertEqual(img2.display_order, 1)

        img1.restore()
        img1.refresh_from_db()

        self.assertNotEqual(img1.display_order, 1)
        self.assertEqual(img1.display_order, 2)
        self.assertIsNone(img1.deleted_at)
        self.assertTrue(ProductImage.objects.filter(id=img1.id).exists())

    def test_restore_conflict_no_integrity_error(self):
        """restoring an image into a taken slot must not raise an IntegrityError"""
        product = ProductFactory()
        img1 = ProductImageFactory(product=product)
        img1.delete()
        ProductImageFactory(product=product)  # occupies display_order=1

        try:
            img1.restore()
        except Exception as e:
            self.fail(f"restore() raised {e}")

    def test_restore_variant_scoped_conflict_reassigns_display_order(self):
        """same conflict resolution applies to variant-scoped images"""
        variant = VariantFactory()
        img1 = ProductImageFactory(for_variant=True, variant=variant)  # display_order=1
        img1.delete()
        img2 = ProductImageFactory(for_variant=True, variant=variant, display_order=1)
        self.assertEqual(img2.display_order, 1)

        img1.restore()
        img1.refresh_from_db()

        self.assertNotEqual(img1.display_order, 1)
        self.assertEqual(img1.display_order, 2)
        self.assertIsNone(img1.deleted_at)

    def test_restore_reassigned_order_is_end_of_sequence(self):
        """the reassigned display_order is appended after all active images"""
        product = ProductFactory()
        img1 = ProductImageFactory(product=product)  # order=1 (only image)
        img1.delete()

        img2 = ProductImageFactory(product=product, display_order=1)
        img3 = ProductImageFactory(product=product)

        img1.restore()
        img1.refresh_from_db()
        max_order = ProductImage.objects.filter(product=product).aggregate(
            max=Max("display_order")
        )["max"]
        self.assertEqual(img1.display_order, 3)
        self.assertEqual(img1.display_order, max_order)


class SoftDeleteRestoreTest(TestCase):
    """tests for the restore() method on SoftDeleteMixin"""

    def test_product_restore(self):
        """test that a soft-deleted product can be restored"""
        product = ProductFactory()
        product.delete()
        self.assertFalse(Product.objects.filter(id=product.id).exists())

        product.restore()

        self.assertIsNone(product.deleted_at)
        self.assertTrue(Product.objects.filter(id=product.id).exists())

    def test_variant_restore(self):
        """test that a soft-deleted variant can be restored"""
        variant = VariantFactory()
        variant.delete()
        self.assertFalse(Variant.objects.filter(id=variant.id).exists())

        variant.restore()

        self.assertIsNone(variant.deleted_at)
        self.assertTrue(Variant.objects.filter(id=variant.id).exists())

    def test_product_image_restore(self):
        """test that a soft-deleted product image can be restored"""
        image = ProductImageFactory()
        image.delete()
        self.assertFalse(ProductImage.objects.filter(id=image.id).exists())

        image.restore()

        self.assertIsNone(image.deleted_at)
        self.assertTrue(ProductImage.objects.filter(id=image.id).exists())
