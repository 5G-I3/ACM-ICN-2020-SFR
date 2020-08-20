Connecting the Dots: Selective Fragment Recovery in ICNLoWPAN
=============================================================
Code and documentation to reproduce our experimental results.

Code
----
The explicit RIOT version is included as a submodule in this repository
([`RIOT`](./RIOT)).  It is based on the 2020.04 release of RIOT (including
hot-fixes) but also contains all relevant changes to conduct the experiments.
The PRs these changes came from are documented within the git history. For more
information use

```sh
git -C RIOT/ log
```

The [`app`](./app) directory contains the RIOT application required for the
experiments. It can be configured to be either an NDN consumer, forwarder, or
producer. Please refer to its [README](./app/README.md) for its usage.

The [`scripts`](./scripts) directory contains both scripts to [conduct the
experiments](./scripts/experiment_ctrl), and to [plot their
results](./scripts/plots). Please also refer to their respective READMEs for
their usage.

To handle the rather specific dependencies of the scripts, we recommend using
[`virtualenv`](https://virtualenv.pypa.io):

```sh
virtualenv -p python3 env
source env/bin/activate
```

Usage
-----
You can look into all the code and its documentation to figure everything out,
but the quickest way to start the experiments is to just run (given the nodes in
`descs.example.yaml` are bookable on the IoT-LAB and all requirements on the OS
side are fulfilled, see [scripts
README's](./scripts/experiment_ctrl/README.md)):

```sh
rm -rf env
virtualenv -p python3 env
source env/bin/activate
pip install -r ./scripts/experiment_ctrl/requirements.txt
cp ./scripts/experiment_ctrl/descs.example.yaml \
    ./scripts/experiment_ctrl/descs.yaml
./scripts/experiment_ctrl/setup_exp.sh
```

Documentation
-------------
[Paper](https://doi.org/10.1145/3405656.3418719)
