# Assignment brief

## Purpose

Build and discuss a small quarterly New Keynesian model for Chile. The exercise
connects the neutral real interest rate, intertemporal demand, inflation
dynamics, and an interest-rate rule in a transparent calibrated framework.

## Required analysis

1. Use a three-equation model with an output gap, inflation, and the nominal
   policy rate.
2. Convert annual neutral-rate assumptions of 2%, 3%, and 4% to quarterly
   rates and map each value into the discount factor.
3. Estimate interest-rate persistence with an AR(1) when an appropriate
   Chilean policy-rate series is supplied. Use a documented fallback otherwise.
4. Compare Phillips-curve slopes of 0.07, 0.10, and 0.13.
5. vary the inflation coefficient in the Taylor rule from 1.3 through 2.2,
   keeping the output-gap coefficient at 0.5, and inspect determinacy.
6. Calibrate demand, cost-push, and monetary-policy shocks and interpret
   impulse responses, unconditional moments, and variance decompositions.
7. Produce reproducible code, tables, figures, and a written report that
   distinguishes calibrated, estimated, and synthetic inputs.

## Public-repository rule

Course PDFs are private reference material and must not be copied, paraphrased
too closely, committed, or uploaded. This brief is an original summary of the
project requirements. The repository ignores all PDF files and any directory
named `_private_course_pdfs`.

## Deliverables

The public project contains an Octave-compatible Dynare model, Python
automation, generated sensitivity models, required CSV tables and PNG figures,
and a Portuguese report draft. A complete reproduction starts from the
repository root and uses only relative project paths.
