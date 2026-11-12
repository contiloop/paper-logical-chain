# Answer key: the four gaps in the first draft of the Beyond RLHF chain

For the four-gap test of the reviewer. The chain under test is `beyond-rlhf-first-draft-chain.md` in this folder, a first draft of a chain for the paper "Beyond RLHF: A Unified Theoretical Framework of Alignment" (arXiv 2506.01523v2). The person read that draft and could not follow it at the four places below. No agent under test may see this file.

## How the test counts

A reviewer with a fresh context is given the draft as a complete chain, for a final review, and is told nothing else. The test passes when its review reports all four gaps. Gap 4 counts only when the review asks both of its questions.

The draft links files of an earlier design that no longer exist. An issue about such a link counts neither for nor against.

## The gaps

Locations are in the paper: section, heading, paragraph.

### 1. Step 8: a reward model is called a language model in another form, with no reason

- **What the reader asks:** why is a reward model a language model?
- **What the paper says:** under the paper's assumption the reward is γ·ln π(a|x) up to a constant, so a reward model defines a language model by π(a|x) ∝ exp(R(x,a)/γ). `[§4, Reward model ¶1]`

### 2. Step 10: reverse KL is said to give "reward plus entropy", with only the start and the result

- **What the reader asks:** how does substituting the reward model's estimate turn the reverse KL into the RLHF objective plus an entropy term?
- **What the paper says:** the reverse KL is the expected −ln π* minus the entropy of the learned model. Putting the reward model's estimate in place of ln π* gives the reward term, and the normalization constant drops out because only relative rewards matter. `[§5 ¶2]`

### 3. Steps 10 to 13: the objective minimizes the reverse KL and the guarantee bounds the forward KL, and nothing says how the two relate

- **What the reader asks:** the method minimizes one divergence and its guarantee is about the other; how do the two fit?
- **What the paper says:** bounding the forward KL avoids comparing the learned model's coverage with the data's, and Proposition 15 relates the forward and reverse KL errors, at the cost of a constant exponential in R. `[§5, Why does reverse KL attain a better bound? ¶1–2]`

### 4. Step 3: existing guarantees are said to be incomparable, with no instance, and with no word on how this fits step 1

Two questions. Both must be asked.

- **What the reader asks first:** which existing analyses, and what does each one guarantee?
- **What the paper says:** Appendix A lists what each prior analysis bounds: policy value or regret, and in one case a forward KL to an optimal policy. `[§A, Theoretical analyses of preference optimization ¶1–2]`
- **What the reader asks second:** step 1 says theory takes the RLHF objective as its goal, and step 3 says each method is analyzed toward a different target; how do both hold?
- **What the paper says:** nothing. How "often the RLHF objective or its variants" `[§1 ¶1–2]` fits "different theoretical targets" `[§1 ¶4]` the paper does not say. This part is a gap of the paper's, and a chain can only say so.
