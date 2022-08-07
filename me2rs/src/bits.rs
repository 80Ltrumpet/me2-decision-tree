//! This module defines operations for querying and manipulating unsigned
//! integers as bitsets.

mod unsigned;

use std::iter::FusedIterator;

use unsigned::Unsigned;

/// Returns an iterator over all set bits in `value` from the least significant
/// bit to the most significant bit.
///
/// # Example
///
/// ```
/// let mut iter = me2::bits::bits(0x321u16);
/// assert_eq!(iter.next(), Some(0x001));
/// assert_eq!(iter.next(), Some(0x020));
/// assert_eq!(iter.next(), Some(0x100));
/// assert_eq!(iter.next(), Some(0x200));
/// assert_eq!(iter.next(), None);
/// ```
pub fn bits<T: Unsigned>(value: T) -> BitValueIterator<T> {
    BitValueIterator::new(value)
}

/// Returns an iterator over the indices of the set bits in `value` from the
/// least significant bit to the most significant bit.
///
/// # Example
///
/// ```
/// let mut iter = me2::bits::indices(0x45u8);
/// assert_eq!(iter.next(), Some(0));
/// assert_eq!(iter.next(), Some(2));
/// assert_eq!(iter.next(), Some(6));
/// assert_eq!(iter.next(), None);
/// ```
pub fn indices<T: Unsigned>(value: T) -> BitIndexIterator<T> {
    BitIndexIterator::new(value)
}

/// Finds the index of the first (least significant) set bit in `value`. If no
/// bits are set, returns None.
///
/// # Examples
///
/// ```
/// use me2::bits;
/// assert_eq!(bits::ffs(32u8), Some(5));
/// assert_eq!(bits::ffs(0x400000u32), Some(22));
/// assert_eq!(bits::ffs(0u8), None);
/// ```
pub fn ffs<T: Unsigned>(value: T) -> Option<u8> {
    if value == T::zero() {
        None
    } else {
        Some(value.trailing_zeros() as u8)
    }
}

/// Finds the value of the first (least significant) set bit in `value`. If no
/// bits are set, returns zero.
///
/// # Examples
///
/// ```
/// use me2::bits;
/// assert_eq!(bits::fsb(42u8), 2);
/// assert_eq!(bits::fsb(0xb00u16), 0x100);
/// assert_eq!(bits::fsb(0u8), 0);
/// ```
pub fn fsb<T: Unsigned>(value: T) -> T {
    let zero = T::zero();
    if value == zero {
        zero
    } else {
        T::one() << value.trailing_zeros() as u8
    }
}

/// Creates a bit mask with the first (least significant) `len` bits set. If
/// `len` is greater than the number of bits in `T`, all bits will be set in
/// the return value.
///
/// # Example
///
/// ```
/// let mask: u8 = me2::bits::mask(3);
/// assert_eq!(mask, 0b111);
/// let mask: u16 = me2::bits::mask(20);
/// assert_eq!(mask, 0xffff);
/// ```
pub fn mask<T: Unsigned>(len: u8) -> T {
    if (len as u32) < T::bits() {
        let one = T::one();
        (one << len) - one
    } else {
        T::max()
    }
}

/// Creates a bit mask where only the trailing zeros in `value` are set. If
/// the least significant bit of `value` is set, returns zero.
///
/// # Examples
///
/// ```
/// use me2::bits;
/// assert_eq!(bits::mtz(0x38u8), 0x7);
/// assert_eq!(bits::mtz(0u64), 0);
/// ```
pub fn mtz<T: Unsigned>(value: T) -> T {
    let zero = T::zero();
    if value == zero {
        zero
    } else {
        mask(value.trailing_zeros() as u8)
    }
}

/// Iterates through the set bit values of a bit mask. Use the `each` free
/// function instead of constructing `BitValueIterator<T>` directly.
pub struct BitValueIterator<T: Unsigned> {
    value: T,
    mask: T,
}

impl<T: Unsigned> BitValueIterator<T> {
    fn new(value: T) -> Self {
        BitValueIterator {
            value,
            mask: T::one(),
        }
    }
}

impl<T: Unsigned> Iterator for BitValueIterator<T> {
    type Item = T;

    fn next(&mut self) -> Option<Self::Item> {
        let zero = T::zero();
        let mut result = None;
        while result.is_none() && self.mask != zero && self.mask < self.value {
            if (self.mask & self.value) != zero {
                result = Some(self.mask)
            }
            self.mask <<= 1;
        }
        result
    }
}

impl<T: Unsigned> FusedIterator for BitValueIterator<T> {}

/// Iterates through the indices of the set bit values of a bit mask. Use the
/// `indices` free function instead of constructing `BitIndexIterator<T>`
/// directly.
pub struct BitIndexIterator<T: Unsigned> {
    value: T,
    mask: T,
    index: u8,
}

impl<T: Unsigned> BitIndexIterator<T> {
    fn new(value: T) -> Self {
        BitIndexIterator {
            value,
            mask: T::one(),
            index: 0,
        }
    }
}

impl<T: Unsigned> Iterator for BitIndexIterator<T> {
    type Item = u8;

    fn next(&mut self) -> Option<Self::Item> {
        let zero = T::zero();
        let mut result = None;
        while result.is_none() && self.mask != zero && self.mask < self.value {
            if (self.mask & self.value) != zero {
                result = Some(self.index);
            }
            self.mask <<= 1;
            self.index += 1;
        }
        result
    }
}

impl<T: Unsigned> FusedIterator for BitIndexIterator<T> {}

#[cfg(test)]
mod test {
    #[test]
    fn each() {
        assert_eq!(super::bits(42u8).collect::<Vec<_>>(), vec![2, 8, 32]);
        assert_eq!(super::bits(0u8).collect::<Vec<_>>(), vec![]);
    }

    #[test]
    fn indices() {
        assert_eq!(
            super::indices(0x69u8).collect::<Vec<_>>(),
            vec![0, 3, 5, 6]
        );
        assert_eq!(super::indices(0u8).collect::<Vec<_>>(), vec![]);
    }

    #[test]
    fn ffs() {
        assert_eq!(super::ffs(0x2000u16), Some(13));
        assert_eq!(super::ffs(42u8), Some(1));
        assert_eq!(super::ffs(0u8), None);
    }

    #[test]
    fn fsb() {
        assert_eq!(super::fsb(64u8), 64);
        assert_eq!(super::fsb(0xf00db8u32), 8);
        assert_eq!(super::fsb(0u8), 0);
    }

    #[test]
    fn mask() {
        assert_eq!(super::mask::<u8>(0), 0);
        assert_eq!(super::mask::<u8>(5), 0b11111);
        assert_eq!(super::mask::<u16>(9), 0x1ff);
        assert_eq!(super::mask::<u32>(31), 0x7fffffff);
        assert_eq!(super::mask::<u64>(33), 0x1ffffffff);
    }

    #[test]
    fn mtz() {
        assert_eq!(super::mtz(0xb00u16), 0xff);
        assert_eq!(super::mtz(0u8), 0);
    }
}
