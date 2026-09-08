/**
 * Embedded Standard Academic Reference Corpus
 * Allows Plagiarism Detector Pro CLI & NPM package to operate 100% offline
 * with zero external Python or server dependencies.
 */

const DEFAULT_ACADEMIC_CORPUS = [
    {
        filename: "machine_learning_foundations.txt",
        text: "Machine learning and artificial intelligence utilize statistical learning theory to infer patterns from high-dimensional data. Neural network optimization leverages backpropagation and stochastic gradient descent across non-convex loss surfaces. In natural language processing, self-attention mechanisms and transformer architectures allow parallel contextual encoding across massive token sequences. Generalization bounds rely on structural risk minimization, regularization penalties, and cross-validation protocols."
    },
    {
        filename: "ai_and_computing.txt",
        text: "Artificial intelligence and computational systems rely on discrete mathematics, algorithmic complexity theory, and parallel computing architectures. Asymptotic efficiency is quantified through Big O notation to bound time and space resource utilization. Distributed consensus algorithms ensure fault tolerance across networked nodes in asynchronous environments. Modern deep learning hardware accelerators utilize tensor processing units and high-bandwidth memory to sustain matrix multiplication throughput."
    },
    {
        filename: "data_analytics_and_diamond_pricing.txt",
        text: "In empirical statistical modeling, multivariable linear regression estimates conditional expectations while isolating confounding covariates. For instance, in diamond pricing analytics, carat weight exhibits non-linear exponential relationships with market valuation, requiring logarithmic transformations or polynomial terms. Collinearity between spatial dimensions (x, y, z) and mass must be diagnosed via variance inflation factors to avoid variance inflation in coefficient estimates."
    },
    {
        filename: "simpsons_paradox_and_statistics.txt",
        text: "Simpson's Paradox occurs when statistical trends appearing in aggregated groups disappear or reverse when the data is disaggregated into underlying subgroups. This phenomenon highlights the critical necessity of causal graphs and confounding variable stratification. Observational studies without random assignment cannot establish causal directionality without conditioning on backdoor adjustment sets or utilizing instrumental variable estimators."
    },
    {
        filename: "crispr_gene_editing_and_biotechnology.txt",
        text: "Clustered Regularly Interspaced Short Palindromic Repeats (CRISPR) and CRISPR-associated endonuclease proteins represent a transformative paradigm in genomic biotechnology. Synthetic single-guide RNAs (sgRNAs) direct Cas9 to induce site-specific double-strand breaks in target genomic sequences. Cellular repair proceeds through error-prone non-homologous end joining (NHEJ) or high-fidelity homology-directed repair (HDR), facilitating precision gene knockouts and targeted nucleotide substitutions."
    },
    {
        filename: "cybersecurity_fundamentals.txt",
        text: "Cybersecurity is the practice of defending electronic systems, networks, devices, and data from malicious digital attacks and unauthorized access. Modern defense-in-depth strategies integrate asymmetric public-key cryptography, zero-trust network architectures, role-based access control, and behavioral intrusion detection systems. Threat modeling systematically analyzes attack vectors, privilege escalation pathways, and data exfiltration risks."
    },
    {
        filename: "cloud_computing_and_distributed_systems.txt",
        text: "Cloud computing architectures deliver elastic on-demand compute, storage, and networking resources via distributed virtualization infrastructure. Microservice architectures partition monolithic software systems into loosely coupled, independently deployable services communicating over gRPC or RESTful APIs. High-availability distributed systems navigate the trade-offs formalised by the CAP theorem between consistency, availability, and partition tolerance."
    },
    {
        filename: "ethics_in_artificial_intelligence.txt",
        text: "Ethical artificial intelligence systems require algorithmic fairness, transparency, accountability, and robust safety guardrails. Automated decision-making algorithms can inadvertently perpetuate and amplify societal biases embedded in historical training datasets. Mitigating algorithmic bias requires demographic parity constraints, equalized odds metrics, model interpretability frameworks, and continuous human-in-the-loop auditing."
    }
];

module.exports = { DEFAULT_ACADEMIC_CORPUS };
