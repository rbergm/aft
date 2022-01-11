
def flatten(deep_list):
    """Extracts the items from a list of lists into a single list.

    Consider a list [[1,2,3], [4,5,6]]. Calling flatten on this list would
    yield [1,2,3,4,5,6].
    """
    return [item for sublist in deep_list for item in sublist]


def select(df, **kwargs):
    """Provides a straightforward value-based access to subsets of a data
    frame.

    E.g. a data frame with columns col_a, col_b and col_c can be selected as
    follows: select(df, col_a=42, col_c="foo"). This will return all rows from
    df, where col_a has the value 42 and col_c has the value "foo".
    """
    if not kwargs:
        return df
    predicates = [df[key] == val for key, val in kwargs.items()]
    condition = predicates[0]
    if len(condition) > 1:
        for pred in predicates[1:]:
            condition &= pred
    return df.loc[condition]

def unwrap(singleton_series):
    """For a pandas series with just a single element, provide that element.
    
    If the series contains multiple entries, a ValueError will be raised.
    """
    if len(singleton_series) > 1:
        raise ValueError("Not a singleton series")
    return singleton_series.values[0]
