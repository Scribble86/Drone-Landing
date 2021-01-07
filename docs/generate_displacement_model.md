# Generating a displacement model

Currently, the software uses the Sklearn library to generate a machine learning model. This is a possible area of
improvement, as other machine learning libraries may be better suited for the task. Regardless, to generate a machine
learning model:

You may need to install some `pip` dependencies first. If that is the case, run:

```bash
pip install -r requirements_gen_model.txt
```

Then, you can generate the model like so:

```bash
python scripts/generate_displacement_model.py
```

The generation script takes a significant amount of time, even on a desktop computer. It takes even longer on the Pi.
This is unfortunate, because the model is saved as a [pickle](https://docs.python.org/3/library/pickle.html), and
pickles are not cross-architecture compatible. The pickles are checked into git due to the amount of time that it takes
to generate them. Thus, the Git branches `master` and `aarch` actually have different pickles. Forgetting this makes it
easy to make a bad merge between them. Unfortunately, we weren't able to come up with a better solution in the time we
had. See [Technical Debt](technical_debt.md).

## About the model

Using the tools provided to us by Sklearn, we found that the best model was the `MLPRegressor` with these
hyperparameters:

```
hidden_layer_sizes: [16, 16, 16, 16]
activation: 'tanh'
```

We found that the above hyperparameters produced a model with metrics:

```
R^2 = 0.9995724996480986
Mean Absolute Error = 0.046654097285850675
Mean Squared Error = 0.0038547041181930725
Explained Variance = 0.9996747711831241
```

However, we encourage the reader to attempt to improve the model's performance by playing with its hyperparameters. 
Despite the results above, there is still potential for improvement.
