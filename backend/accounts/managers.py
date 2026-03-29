from django.contrib.auth.models import BaseUserManager


# custom manager for user creation using email as the unique identifier
class CustomUserManager(BaseUserManager):
    # creates and returns a standard user with a hashed password
    def create_user(self, email, first_name, last_name, password=None, **extra_args):
        if not email:
            raise ValueError("email is required")
        if not first_name:
            raise ValueError("first_name is required")
        if not last_name:
            raise ValueError("last_name is required")

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            **extra_args,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    # creates and returns a superuser with staff and superuser flags set
    def create_superuser(
        self, email, first_name, last_name, password=None, **extra_args
    ):
        extra_args.setdefault("is_staff", True)
        extra_args.setdefault("is_superuser", True)
        extra_args.setdefault("is_active", True)

        # guard against explicitly passing False for required superuser flags
        if extra_args.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_args.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, first_name, last_name, password, **extra_args)
