use std::ops::{BitAnd, Shl, ShlAssign, Sub};

pub trait Unsigned:
    Copy
    + BitAnd<Output = Self>
    + PartialOrd<Self>
    + Shl<u8, Output = Self>
    + ShlAssign<u8>
    + Sub<Self, Output = Self>
{
    fn bits() -> u32;
    fn max() -> Self;
    fn one() -> Self;
    fn trailing_zeros(self) -> u32;
    fn zero() -> Self;
}

macro_rules! impl_Unsigned_for {
    ($($t:ty),*) => {$(
        impl Unsigned for $t {
            fn bits() -> u32 { <$t>::BITS }
            fn max() -> Self { <$t>::MAX }
            fn one() -> Self { 1 }
            fn zero() -> Self { 0 }
            fn trailing_zeros(self) -> u32 {
                <$t>::trailing_zeros(self)
            }
        }
    )*};
}

impl_Unsigned_for!(u8, u16, u32, u64, usize);
