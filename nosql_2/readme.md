# Завдання 2 — Семантичний пошук за науковими статтями

RAG-пайплайн пошуку по статтях arXiv: **Pinecone** (векторна БД) + **allenai/specter2_base** (ембеддинги) + **BM25** і **Reciprocal Rank Fusion** для гібридного пошуку.

Скрипти запускаються послідовно:

| Скрипт | Призначення |
|---|---|
| `scripts/01_prepare_data.py` | підготовка підмножини датасету arXiv (10 000 статей) → parquet |
| `scripts/02_embed.py` | генерація нормалізованих ембеддингів SPECTER2 → `embeddings.npy` |
| `scripts/03_load_to_pinecone.py` | створення індексу `arxiv-papers` і батчеве завантаження |
| `scripts/04_search.py` | семантичний пошук, фільтри за метаданими, порівняння метрик |
| `scripts/05_chunking.py` | fixed-size і semantic chunking, окремі індекси |
| `scripts/06_hybrid_search.py` | BM25 + векторний пошук + RRF |

`.env`, `data/`, `embeddings/` додані в `.gitignore`.

---

## Частина 1 — Підготовка даних і вибір інструментів

**Мета:** завантажити датасет, вибрати і отримати ембеддинги.

### 1.1. Завантаження і підготовка датасету

Вивід `01_prepare_data.py`:

```text
  python .\scripts\01_prepare_data.py            
Читаємо датасет: 10000it [00:00, 79398.93it/s]                                

Завантажено статей: 10000

Розподіл за категоріями (топ-10):
category
astro-ph              1838
hep-th                 680
hep-ph                 671
quant-ph               564
gr-qc                  350
cond-mat.mes-hall      307
cond-mat.str-el        292
cond-mat.mtrl-sci      291
cond-mat.stat-mech     271
math.AG                209
Name: count, dtype: int64

Розподіл за роками:
year
2007    10000
Name: count, dtype: int64

Приклад запису:
{'id': '0704.0001', 'title': 'Calculation of prompt diphoton production cross sections at Tevatron and   LHC energies', 'abstract': 'A fully differential calculation in perturbative quantum chromodynamics is presented for the production of massive photon pairs at hadron colliders. All next-to-leading order perturbative contributions from quark-antiquark, gluon-(anti)quark, and gluon-gluon subprocesses are included, as well as all-orders resummation of initial-state gluon radiation valid at next-to-next-to-leading logarithmic accuracy. The region of phase space is specified in which the calculation is most reliable. Good agreement is demonstrated with data from the Fermilab Tevatron, and predictions are made for more detailed tests with CDF and DO data. Predictions are shown for distributions of diphoton pairs produced at the energy of the Large Hadron Collider (LHC). Distributions of the diphoton pairs from the decay of a Higgs boson are contrasted with those produced from QCD processes at the LHC, showing that enhanced sensitivity to the signal can be obtained with judicious selection of events.', 'authors': 'Balázs C., Berger E. L., Nadolsky P. M., Yuan C. -P.', 'year': 2007, 'category': 'hep-ph'}

Збережено в data\arxiv_subset.parquet
```

### Відповіді на запитання

#### 1. Чим Pinecone відрізняється від Qdrant і Chroma?

Pinecone — це managed cloud-сервіс для векторного пошуку. Його зручно обрати для production, коли потрібне масштабування і мінімум DevOps. Мінус — комерційна модель і залежність від сервісу.

Qdrant — open-source векторна база, яку можна запускати самостійно або використовувати через Qdrant Cloud. Її варто обрати, коли потрібен контроль над інфраструктурою, даними і розгортанням.

Chroma — open-source інструмент, зручний для локальних RAG-прототипів, навчальних проєктів і MVP. Для великого production-навантаження я б швидше обрав Pinecone або Qdrant.

#### 2. Чому specter2_base, а не all-MiniLM-L6-v2?

specter2_base обрана тому, що це модель саме для наукових текстів. У картці HuggingFace написано, що SPECTER2 є successor to SPECTER і призначена для створення task-specific embeddings for scientific tasks. Також зазначено, що за комбінацією title і abstract наукової статті або короткого текстового запиту модель може створювати ефективні embeddings для downstream applications.

all-MiniLM-L6-v2 є універсальною embedding-моделлю, але вона не спеціалізована саме на наукових публікаціях. Тому для пошуку по arXiv-статтях specter2_base є більш доречним вибором.

#### 3. Рекомендована метрика схожості

У картці specter2_base вказано, що це base model для використання разом з adapters; для загального embedding-використання HuggingFace-картка рекомендує allenai/specter2.

У цьому проєкті ембеддинги створюються з normalize_embeddings=True, тобто мають одиничну довжину. Тому логічно використовувати cosine similarity в Pinecone. Це важливо, бо метрика індексу має відповідати способу порівняння векторів. Якщо вибрати неправильну метрику, пошук найближчих статей може давати менш релевантні результати.

### 1.3. Отримання ембеддингів

Вивід `02_embed.py`:

```text
No sentence-transformers model found with name allenai/specter2_base. Creating a new one with mean pooling.
Generating embeddings...
Batches: 100%|████████████████████████████████████| 157/157 [23:02<00:00,  8.81s/it]
Embeddings shape: (10000, 768)
Embedding dimension: 768
First embedding norm: 1.0000
Embeddings saved to: embeddings\embeddings.npy
```

#### Чому для нормалізованих ембеддингів cosine similarity еквівалентна dot product?

Косинусна схожість між двома векторами рахується так:

```
cosine(a, b) = (a · b) / (||a|| · ||b||)
```

Тут `a · b` — скалярний добуток, `||a||` і `||b||` — довжини векторів.

Якщо ембеддинги нормалізовані, то їхня довжина дорівнює 1: `||a|| = 1`, `||b|| = 1`. Тоді формула спрощується:

```
cosine(a, b) = (a · b) / (1 · 1) = a · b
```

Тобто для нормалізованих ембеддингів косинусна схожість і скалярний добуток дають однакове значення.

Саме тому при normalize_embeddings=True результати пошуку за cosine similarity і dot product майже або повністю збігаються.

---

## Частина 2 — Завантаження даних і метадані

Вивід `03_load_to_pinecone.py`:

```text
python .\scripts\03_load_to_pinecone.py
Loading dataset from data\arxiv_subset.parquet
Loading embeddings from embeddings\embeddings.npy
Dataset shape: (10000, 6)
Embeddings shape: (10000, 768)
Creating Pinecone index: arxiv-papers
Uploading to Pinecone: 100%|████████████████████████| 50/50 [01:09<00:00,  1.39s/it]
Upload completed.

Index stats:
{'dimension': 768,
 'index_fullness': 0.0,
 'namespaces': {'': {'vector_count': 10000}},
 'total_vector_count': 10000}
```

#### Чому abstract обрізається до 500 символів?

Abstract обрізається в метаданих Pinecone, щоб не перевищувати ліміт розміру metadata для одного вектора. Pinecone підтримує до 40 KB metadata на один record, тому повний текст анотації не варто зберігати всередині metadata, особливо якщо текстів багато або вони довгі.

У Pinecone краще зберігати тільки службову інформацію для пошуку і фільтрації: arxiv_id, title, year, category і короткий фрагмент abstract. Повний abstract доцільно залишати в локальному parquet-файлі і після пошуку підтягувати його за arxiv_id.

Тобто Pinecone використовується для швидкого векторного пошуку, а повні тексти зберігаються окремо як основне джерело даних.

---

## Частина 3 — Пошукові запити

<details>
<summary>Повний вивід <code>04_search.py</code> (семантичний пошук, фільтри A/B, три метрики)</summary>

```text
python .\scripts\04_search.py          

Loading model: allenai/specter2_base
No sentence-transformers model found with name allenai/specter2_base. Creating a new one with mean pooling.
Loading dataset from data\arxiv_subset.parquet
Loading embeddings from embeddings\embeddings.npy

================================================================================
Query: teaching machines to recognize objects in pictures

=== Pinecone: Pure semantic search without filters ===

#1
Score: 0.8288
Title: Capturing knots in polymers
Category: cond-mat.soft
Year: 2007.0
Abstract: This paper visualizes a knot reduction algorithm...

#2
Score: 0.8263
Title: Symbolic sensors : one solution to the numerical-symbolic interface
Category: physics.ins-det
Year: 2007.0
Abstract: This paper introduces the concept of symbolic sensor as an extension of the smart sensor one. Then, the links between the physical world and the symbolic one are introduced. The creation of symbols is proposed within the frame of the pretopology theory. In order to adapt the sensor to the measuremen...

#3
Score: 0.8256
Title: The Mathematics
Category: math.HO
Year: 2007.0
Abstract: This is an essay that considering the knowledge structure and language of a different nature, attempts to build on an explanation of the object of study and characteristics of the mathematical science. We end up with a learning cycle of mathematics and a paradigm for education, namely Learn to struc...

#4
Score: 0.8170
Title: Modeling the field of laser welding melt pool by RBFNN
Category: physics.comp-ph
Year: 2007.0
Abstract: Efficient control of a laser welding process requires the reliable prediction of process behavior. A statistical method of field modeling, based on normalized RBFNN, can be successfully used to predict the spatiotemporal dynamics of surface optical activity in the laser welding process. In this arti...

#5
Score: 0.8146
Title: Why should anyone care about computing with anyons?
Category: quant-ph
Year: 2007.0
Abstract: In this article we present a pedagogical introduction of the main ideas and recent advances in the area of topological quantum computation. We give an overview of the concept of anyons and their exotic statistics, present various models that exhibit topological behavior, and we establish their relat...

=== Local metrics: Pure semantic search without filters ===

--- Cosine similarity ---

#1
Score: 0.8294
Title: Capturing knots in polymers
Category: cond-mat.soft
Year: 2007
Abstract: This paper visualizes a knot reduction algorithm...

#2
Score: 0.8260
Title: Symbolic sensors : one solution to the numerical-symbolic interface
Category: physics.ins-det
Year: 2007
Abstract: This paper introduces the concept of symbolic sensor as an extension of the smart sensor one. Then, the links between the physical world and the symbolic one are introduced. The creation of symbols is proposed within the frame of the pretopology theory. In order to adapt the sensor to the measuremen...

#3
Score: 0.8254
Title: The Mathematics
Category: math.HO
Year: 2007
Abstract: This is an essay that considering the knowledge structure and language of a different nature, attempts to build on an explanation of the object of study and characteristics of the mathematical science. We end up with a learning cycle of mathematics and a paradigm for education, namely Learn to struc...

#4
Score: 0.8181
Title: Modeling the field of laser welding melt pool by RBFNN
Category: physics.comp-ph
Year: 2007
Abstract: Efficient control of a laser welding process requires the reliable prediction of process behavior. A statistical method of field modeling, based on normalized RBFNN, can be successfully used to predict the spatiotemporal dynamics of surface optical activity in the laser welding process. In this arti...

#5
Score: 0.8142
Title: Python for Education: Computational Methods for Nonlinear Systems
Category: nlin.CD
Year: 2007
Abstract: We describe a novel, interdisciplinary, computational methods course that uses Python and associated numerical and visualization libraries to enable students to implement simulations for a number of different course modules. Problems in complex networks, biomechanics, pattern formation, and gene reg...

--- Dot product ---

#1
Score: 0.8294
Title: Capturing knots in polymers
Category: cond-mat.soft
Year: 2007
Abstract: This paper visualizes a knot reduction algorithm...

#2
Score: 0.8260
Title: Symbolic sensors : one solution to the numerical-symbolic interface
Category: physics.ins-det
Year: 2007
Abstract: This paper introduces the concept of symbolic sensor as an extension of the smart sensor one. Then, the links between the physical world and the symbolic one are introduced. The creation of symbols is proposed within the frame of the pretopology theory. In order to adapt the sensor to the measuremen...

#3
Score: 0.8254
Title: The Mathematics
Category: math.HO
Year: 2007
Abstract: This is an essay that considering the knowledge structure and language of a different nature, attempts to build on an explanation of the object of study and characteristics of the mathematical science. We end up with a learning cycle of mathematics and a paradigm for education, namely Learn to struc...

#4
Score: 0.8181
Title: Modeling the field of laser welding melt pool by RBFNN
Category: physics.comp-ph
Year: 2007
Abstract: Efficient control of a laser welding process requires the reliable prediction of process behavior. A statistical method of field modeling, based on normalized RBFNN, can be successfully used to predict the spatiotemporal dynamics of surface optical activity in the laser welding process. In this arti...

#5
Score: 0.8142
Title: Python for Education: Computational Methods for Nonlinear Systems
Category: nlin.CD
Year: 2007
Abstract: We describe a novel, interdisciplinary, computational methods course that uses Python and associated numerical and visualization libraries to enable students to implement simulations for a number of different course modules. Problems in complex networks, biomechanics, pattern formation, and gene reg...

--- L2 distance ---

#1
Score: 0.5842
Title: Capturing knots in polymers
Category: cond-mat.soft
Year: 2007
Abstract: This paper visualizes a knot reduction algorithm...

#2
Score: 0.5899
Title: Symbolic sensors : one solution to the numerical-symbolic interface
Category: physics.ins-det
Year: 2007
Abstract: This paper introduces the concept of symbolic sensor as an extension of the smart sensor one. Then, the links between the physical world and the symbolic one are introduced. The creation of symbols is proposed within the frame of the pretopology theory. In order to adapt the sensor to the measuremen...

#3
Score: 0.5910
Title: The Mathematics
Category: math.HO
Year: 2007
Abstract: This is an essay that considering the knowledge structure and language of a different nature, attempts to build on an explanation of the object of study and characteristics of the mathematical science. We end up with a learning cycle of mathematics and a paradigm for education, namely Learn to struc...

#4
Score: 0.6032
Title: Modeling the field of laser welding melt pool by RBFNN
Category: physics.comp-ph
Year: 2007
Abstract: Efficient control of a laser welding process requires the reliable prediction of process behavior. A statistical method of field modeling, based on normalized RBFNN, can be successfully used to predict the spatiotemporal dynamics of surface optical activity in the laser welding process. In this arti...

#5
Score: 0.6095
Title: Python for Education: Computational Methods for Nonlinear Systems
Category: nlin.CD
Year: 2007
Abstract: We describe a novel, interdisciplinary, computational methods course that uses Python and associated numerical and visualization libraries to enable students to implement simulations for a number of different course modules. Problems in complex networks, biomechanics, pattern formation, and gene reg...

================================================================================
Query: reinforcement learning
Filter A: category = cs.LG, year >= 2021

=== Pinecone: Example A: cs.LG, year >= 2021 ===
No results found.

=== Local metrics: Example A: cs.LG, year >= 2021 ===
No local results found.

================================================================================
Query: reinforcement learning
Filter B: year < 2015

=== Pinecone: Example B: year < 2015, any category ===

#1
Score: 0.8445
Title: Multi-Agent Modeling Using Intelligent Agents in the Game of Lerpa
Category: cs.MA
Year: 2007.0
Abstract: Game theory has many limitations implicit in its application. By utilizing multiagent modeling, it is possible to solve a number of problems that are unsolvable using traditional game theory. In this paper reinforcement learning is applied to neural networks to create intelligent agents...

#2
Score: 0.8194
Title: Introduction to Phase Transitions in Random Optimization Problems
Category: cond-mat.stat-mech
Year: 2007.0
Abstract: Notes of the lectures delivered in Les Houches during the Summer School on Complex Systems (July 2006)....

#3
Score: 0.8102
Title: Architecture for Pseudo Acausal Evolvable Embedded Systems
Category: cs.NE
Year: 2007.0
Abstract: Advances in semiconductor technology are contributing to the increasing complexity in the design of embedded systems. Architectures with novel techniques such as evolvable nature and autonomous behavior have engrossed lot of attention. This paper demonstrates conceptually evolvable embedded systems ...

#4
Score: 0.8010
Title: Why only few are so successful ?
Category: physics.pop-ph
Year: 2007.0
Abstract: In many professons employees are rewarded according to their relative performance. Corresponding economy can be modeled by taking $N$ independent agents who gain from the market with a rate which depends on their current gain. We argue that this simple realistic rate generates a scale free distribut...

#5
Score: 0.7993
Title: Opinion Dynamics and Sociophysics
Category: physics.soc-ph
Year: 2007.0
Abstract: No abstract given. Contents:   I. Definition and Introduction   II. Schelling Model   III. Opinion Dynamics   IV. Languages, Hierarchies and Football   V. Future Directions...

=== Local metrics: Example B: year < 2015, any category ===

--- Cosine similarity ---

#1
Score: 0.8454
Title: Multi-Agent Modeling Using Intelligent Agents in the Game of Lerpa
Category: cs.MA
Year: 2007
Abstract: Game theory has many limitations implicit in its application. By utilizing multiagent modeling, it is possible to solve a number of problems that are unsolvable using traditional game theory. In this paper reinforcement learning is applied to neural networks to create intelligent agents...

#2
Score: 0.8190
Title: Introduction to Phase Transitions in Random Optimization Problems
Category: cond-mat.stat-mech
Year: 2007
Abstract: Notes of the lectures delivered in Les Houches during the Summer School on Complex Systems (July 2006)....

#3
Score: 0.8103
Title: Architecture for Pseudo Acausal Evolvable Embedded Systems
Category: cs.NE
Year: 2007
Abstract: Advances in semiconductor technology are contributing to the increasing complexity in the design of embedded systems. Architectures with novel techniques such as evolvable nature and autonomous behavior have engrossed lot of attention. This paper demonstrates conceptually evolvable embedded systems ...

#4
Score: 0.8017
Title: Why only few are so successful ?
Category: physics.pop-ph
Year: 2007
Abstract: In many professons employees are rewarded according to their relative performance. Corresponding economy can be modeled by taking $N$ independent agents who gain from the market with a rate which depends on their current gain. We argue that this simple realistic rate generates a scale free distribut...

#5
Score: 0.8011
Title: Opinion Dynamics and Sociophysics
Category: physics.soc-ph
Year: 2007
Abstract: No abstract given. Contents:   I. Definition and Introduction   II. Schelling Model   III. Opinion Dynamics   IV. Languages, Hierarchies and Football   V. Future Directions...

--- Dot product ---

#1
Score: 0.8454
Title: Multi-Agent Modeling Using Intelligent Agents in the Game of Lerpa
Category: cs.MA
Year: 2007
Abstract: Game theory has many limitations implicit in its application. By utilizing multiagent modeling, it is possible to solve a number of problems that are unsolvable using traditional game theory. In this paper reinforcement learning is applied to neural networks to create intelligent agents...

#2
Score: 0.8190
Title: Introduction to Phase Transitions in Random Optimization Problems
Category: cond-mat.stat-mech
Year: 2007
Abstract: Notes of the lectures delivered in Les Houches during the Summer School on Complex Systems (July 2006)....

#3
Score: 0.8103
Title: Architecture for Pseudo Acausal Evolvable Embedded Systems
Category: cs.NE
Year: 2007
Abstract: Advances in semiconductor technology are contributing to the increasing complexity in the design of embedded systems. Architectures with novel techniques such as evolvable nature and autonomous behavior have engrossed lot of attention. This paper demonstrates conceptually evolvable embedded systems ...

#4
Score: 0.8017
Title: Why only few are so successful ?
Category: physics.pop-ph
Year: 2007
Abstract: In many professons employees are rewarded according to their relative performance. Corresponding economy can be modeled by taking $N$ independent agents who gain from the market with a rate which depends on their current gain. We argue that this simple realistic rate generates a scale free distribut...

#5
Score: 0.8011
Title: Opinion Dynamics and Sociophysics
Category: physics.soc-ph
Year: 2007
Abstract: No abstract given. Contents:   I. Definition and Introduction   II. Schelling Model   III. Opinion Dynamics   IV. Languages, Hierarchies and Football   V. Future Directions...

--- L2 distance ---

#1
Score: 0.5561
Title: Multi-Agent Modeling Using Intelligent Agents in the Game of Lerpa
Category: cs.MA
Year: 2007
Abstract: Game theory has many limitations implicit in its application. By utilizing multiagent modeling, it is possible to solve a number of problems that are unsolvable using traditional game theory. In this paper reinforcement learning is applied to neural networks to create intelligent agents...

#2
Score: 0.6017
Title: Introduction to Phase Transitions in Random Optimization Problems
Category: cond-mat.stat-mech
Year: 2007
Abstract: Notes of the lectures delivered in Les Houches during the Summer School on Complex Systems (July 2006)....

#3
Score: 0.6160
Title: Architecture for Pseudo Acausal Evolvable Embedded Systems
Category: cs.NE
Year: 2007
Abstract: Advances in semiconductor technology are contributing to the increasing complexity in the design of embedded systems. Architectures with novel techniques such as evolvable nature and autonomous behavior have engrossed lot of attention. This paper demonstrates conceptually evolvable embedded systems ...

#4
Score: 0.6297
Title: Why only few are so successful ?
Category: physics.pop-ph
Year: 2007
Abstract: In many professons employees are rewarded according to their relative performance. Corresponding economy can be modeled by taking $N$ independent agents who gain from the market with a rate which depends on their current gain. We argue that this simple realistic rate generates a scale free distribut...

#5
Score: 0.6308
Title: Opinion Dynamics and Sociophysics
Category: physics.soc-ph
Year: 2007
Abstract: No abstract given. Contents:   I. Definition and Introduction   II. Schelling Model   III. Opinion Dynamics   IV. Languages, Hierarchies and Football   V. Future Directions...

Abstract: We consider the problem of reinforcement learning using function approximation, where the approximating basis can change dynamically while interacting with the environment. A motivation for such an approach is maximizing the value function fitness to...
```

</details>

### Відповіді на теоретичні запитання

#### Чи збігаються топ-5 для cosine і dot product і чому?

Так, у нашому експерименті топ-5 для cosine similarity і dot product збігаються або майже повністю збігаються. Це відбувається тому, що ембеддинги були нормалізовані через normalize_embeddings=True.

Для нормалізованих векторів їхня довжина дорівнює 1, тому формула cosine similarity спрощується до звичайного скалярного добутку. Через це обидві метрики дають однаковий порядок найближчих документів.

#### Чи відрізняються результати для L2 і чому?

Результати для L2-distance можуть трохи відрізнятися, але для нормалізованих ембеддингів вони часто дуже схожі на cosine і dot product. Причина в тому, що для векторів одиничної довжини менша L2-відстань зазвичай відповідає більшій косинусній схожості.

Головна різниця в інтерпретації: для cosine і dot product більше значення означає більшу схожість, а для L2-distance навпаки — менше значення означає більшу схожість.

#### Що сталося б, якби ембеддинги не були нормалізовані?

Якби ембеддинги не були нормалізовані, cosine similarity і dot product вже не були так подібні. Dot product враховував би не тільки напрям вектора, а й його довжину. Через це довші або “сильніші” за нормою вектори могли б отримувати вищі оцінки, навіть якщо вони не є найбільш семантично схожими.

У такому випадку результати пошуку за cosine, dot product і L2 могли б значно відрізнятися. Тому нормалізація важлива для стабільного порівняння ембеддингів за змістом.

---

## Частина 4 — Chunking

<details>
<summary>Повний вивід <code>05_chunking.py</code> (fixed vs semantic chunks, тестові запити)</summary>

```text
No sentence-transformers model found with name allenai/specter2_base. Creating a newone with mean pooling.
Selected articles: 30
                                                  title  ... abstract_word_count
7848              The SN 1987A Link to Gamma-Ray Bursts  ...                 338
4980  X-ray Timing of PSR J1852+0040 in Kesteven 79:...  ...                 318
8063  High energy afterglows and flares from Gamma-R...  ...                 314
8345  A Systematic Study of the Final Masses of Gas ...  ...                 313
4068  An Imaging Survey for Extrasolar Planets aroun...  ...                 312

[5 rows x 4 columns]
Creating index: arxiv-chunks-fixed
Creating index: arxiv-chunks-semantic

Fixed chunks: 117
Semantic chunks: 96

Uploading fixed chunks...
Batches: 100%|████████████████████████████████████████| 2/2 [00:28<00:00, 14.13s/it]
Uploading batches: 100%|██████████████████████████████| 2/2 [00:05<00:00,  2.52s/it]

Uploading semantic chunks...
Batches: 100%|████████████████████████████████████████| 2/2 [00:20<00:00, 10.48s/it]
Uploading batches: 100%|██████████████████████████████| 1/1 [00:08<00:00,  8.90s/it]

=== Fixed chunks: reinforcement learning ===

#1
Score: 0.7307
Title: Geochemistry of U and Th and its Influence on the Origin and Evolution   of the Crust of Earth and the Biological Evolution
Chunk: believe that a comprehensive exploration on energy sources and their evolution is a good way to build bridges between different disciplines of science in order tobetter understand the Earth and planets....

#2
Score: 0.7227
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: the latter show different and nonlinear offsets for population A and B sources. A significant number of sources also show narrow line CIV 1549 emission. We present a recipe for CIV 1549 narrow component extraction....

#3
Score: 0.7226
Title: The Color Magnitude Distribution of Field Galaxies to z~3: the evolution   and modeling of the blue sequence
Chunk: ~ 6 from z = 2.7 to z = 0.5, as does their contribution to the total rest-frame V-band luminosity density. We are likely viewing the progressive formation of red,passively evolving galaxies....

#4
Score: 0.7197
Title: Conjectures on exact solution of three - dimensional (3D) simple orthorhombicIsing lattices
Chunk: methods and the experimental findings. The 3D to 2D crossover phenomenon differs with the 2D to 1D crossover phenomenon and there is a gradual crossover of the exponents from the 3D values to the 2D ones....

#5
Score: 0.7119
Title: Dark matter in the Milky Way, II. the HI gas distribution as a tracer of   the gravitational potential
Chunk: Context. Gas within a galaxy is forced to establish pressure balance against gravitational forces. The shape of an unperturbed gaseous disk can be used to constrain dark matter models. Aims. We derive the 3-D HI volume density distribution for theMilky Way out to a galactocentric radius of 40 kpc a...

=== Semantic chunks: reinforcement learning ===

#1
Score: 0.7255
Title: The SN 1987A Link to Gamma-Ray Bursts
Chunk: There is no need to invent exotica, such as collapsars or hypernovae, to account for GRBs....

#2
Score: 0.7159
Title: Geochemistry of U and Th and its Influence on the Origin and Evolution   of the Crust of Earth and the Biological Evolution
Chunk: We propose that since the Earth and planets were born in a united solar system, there should be some common mechanisms to create the similarities and differences between them. We have tried to develop an integrated view to explain some problems inthe tectonics of Earth and evolution, bio-evolution,...

#3
Score: 0.7125
Title: An Imaging Survey for Extrasolar Planets around 45 Close, Young Stars   with SDI at the VLT and MMT
Chunk: From our survey null result, we can rule out (at the 98% confidence/2.0sigma level) a model planet population using a planet distribution where N(a) $\propto$ constant out to a distance of 45 AU (further model assumptions discussed within)....

#4
Score: 0.7121
Title: Dark matter in the Milky Way, II. the HI gas distribution as a tracer of   the gravitational potential
Chunk: Context. Gas within a galaxy is forced to establish pressure balance against gravitational forces. The shape of an unperturbed gaseous disk can be used to constrain dark matter models. Aims. We derive the 3-D HI volume density distribution for theMilky Way out to a galactocentric radius of 40 kpc a...

#5
Score: 0.7088
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: Narrow line Seyfert 1 (NLSy1, with FWHM H beta < 2000 km/s) sources belong tothis population but do not emerge as a distinct class. The systematic blueshift, widely interpreted as arising in a disk wind/outflow, is not observed in broader lined AGN which we call Population B. We find new correlatio...

=== Fixed chunks: object recognition in images ===

#1
Score: 0.7544
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: the latter show different and nonlinear offsets for population A and B sources. A significant number of sources also show narrow line CIV 1549 emission. We present a recipe for CIV 1549 narrow component extraction....

#2
Score: 0.7535
Title: (Co)cyclic (co)homology of bialgebroids: An approach via (co)monads
Chunk: application, we compute Hochschild and cyclic homology of a groupoid with coefficients, by tracing it back to the group case. In particular, we obtain explicit expressions for ordinary Hochschild and cyclic homology of a groupoid....

#3
Score: 0.7454
Title: The photospheric environment of a solar pore with light bridge
Chunk: Pores are one of the various features forming in the photosphere by the emergence of magnetic field onto the solar surface. They lie at the border between tiny magnetic elements and larger sunspots. Light bridges, in such structures, are bright features separating umbral areas in two or more irregul...

#4
Score: 0.7436
Title: The Color Magnitude Distribution of Field Galaxies to z~3: the evolution   and modeling of the blue sequence
Chunk: ~ 6 from z = 2.7 to z = 0.5, as does their contribution to the total rest-frame V-band luminosity density. We are likely viewing the progressive formation of red,passively evolving galaxies....

#5
Score: 0.7430
Title: Conjectures on exact solution of three - dimensional (3D) simple orthorhombicIsing lattices
Chunk: methods and the experimental findings. The 3D to 2D crossover phenomenon differs with the 2D to 1D crossover phenomenon and there is a gradual crossover of the exponents from the 3D values to the 2D ones....

=== Semantic chunks: object recognition in images ===

#1
Score: 0.7561
Title: The photospheric environment of a solar pore with light bridge
Chunk: Pores are one of the various features forming in the photosphere by the emergence of magnetic field onto the solar surface. They lie at the border between tiny magnetic elements and larger sunspots. Light bridges, in such structures, are bright features separating umbral areas in two or more irregul...

#2
Score: 0.7444
Title: Observations towards early-type stars in the ESO-POP survey: II --   searchesfor intermediate and high velocity clouds
Chunk: The non-detection of CaII K absorption sets a lower distance of 3.2-kpc towards the HVC, which is unsurprising if this feature is indeed related to the MagellanicSystem....

#3
Score: 0.7349
Title: Conjectures on exact solution of three - dimensional (3D) simple orthorhombicIsing lattices
Chunk: We report the conjectures on the three-dimensional (3D) Ising model on simpleorthorhombic lattices, together with the details of calculations for a putative exact solution. Two conjectures, an additional rotation in the fourth curled-up dimensionand the weight factors on the eigenvectors, are prop...

#4
Score: 0.7333
Title: The SN 1987A Link to Gamma-Ray Bursts
Chunk: There is no need to invent exotica, such as collapsars or hypernovae, to account for GRBs....

#5
Score: 0.7311
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: Black hole masses computed from FWHM CIV 1549 BC for about 80 AGN indicate that the CIV 1549 width is a poor virial estimator. Comparison of mass estimates derived from Hbeta BC and CIV 1549 reveals that the latter show different and nonlinear offsets for population A and B sources. A significant nu...

=== Fixed chunks: natural language processing ===

#1
Score: 0.7340
Title: Geochemistry of U and Th and its Influence on the Origin and Evolution   of the Crust of Earth and the Biological Evolution
Chunk: believe that a comprehensive exploration on energy sources and their evolution is a good way to build bridges between different disciplines of science in order tobetter understand the Earth and planets....

#2
Score: 0.7297
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: the latter show different and nonlinear offsets for population A and B sources. A significant number of sources also show narrow line CIV 1549 emission. We present a recipe for CIV 1549 narrow component extraction....

#3
Score: 0.7281
Title: Geochemistry of U and Th and its Influence on the Origin and Evolution   of the Crust of Earth and the Biological Evolution
Chunk: reason, a plate tectonic system can not been developed in these planets. We also emphasize the influence of U and Th in EZ on the development and evolution of life on Earth. We propose that since the Earth and planets were born in a united solar system, there should be some common mechanisms to crea...

#4
Score: 0.7241
Title: (Co)cyclic (co)homology of bialgebroids: An approach via (co)monads
Chunk: application, we compute Hochschild and cyclic homology of a groupoid with coefficients, by tracing it back to the group case. In particular, we obtain explicit expressions for ordinary Hochschild and cyclic homology of a groupoid....

#5
Score: 0.7222
Title: Conjectures on exact solution of three - dimensional (3D) simple orthorhombicIsing lattices
Chunk: methods and the experimental findings. The 3D to 2D crossover phenomenon differs with the 2D to 1D crossover phenomenon and there is a gradual crossover of the exponents from the 3D values to the 2D ones....

=== Semantic chunks: natural language processing ===

#1
Score: 0.7347
Title: Geochemistry of U and Th and its Influence on the Origin and Evolution   of the Crust of Earth and the Biological Evolution
Chunk: We propose that since the Earth and planets were born in a united solar system, there should be some common mechanisms to create the similarities and differences between them. We have tried to develop an integrated view to explain some problems inthe tectonics of Earth and evolution, bio-evolution,...

#2
Score: 0.7158
Title: An Imaging Survey for Extrasolar Planets around 45 Close, Young Stars   with SDI at the VLT and MMT
Chunk: From our survey null result, we can rule out (at the 98% confidence/2.0sigma level) a model planet population using a planet distribution where N(a) $\propto$ constant out to a distance of 45 AU (further model assumptions discussed within)....

#3
Score: 0.7125
Title: The SN 1987A Link to Gamma-Ray Bursts
Chunk: There is no need to invent exotica, such as collapsars or hypernovae, to account for GRBs....

#4
Score: 0.7092
Title: (Co)cyclic (co)homology of bialgebroids: An approach via (co)monads
Chunk: For a (co)monad T_l on a category M, an object X in M, and a functor \Pi: M \to C, there is a (co)simplex Z^*:=\Pi T_l^{* +1} X in C. Our aim is to find criteria for para-(co)cyclicity of Z^*. Construction is built on a distributive law of T_l with a second (co)monad T_r on M, a natural transformati...

#5
Score: 0.7070
Title: CIV 1549 as an Eigenvector 1 Parameter for Active Galactic Nuclei
Chunk: Narrow line Seyfert 1 (NLSy1, with FWHM H beta < 2000 km/s) sources belong tothis population but do not emerge as a distinct class. The systematic blueshift, widely interpreted as arising in a disk wind/outflow, is not observed in broader lined AGN which we call Population B. We find new correlatio...
```

</details>

### Відповіді на теоретичні питання до частини 4

#### Яка стратегія дає більш осмислені чанки?

Більш осмислені чанки дає semantic chunking, тому що він намагається не розривати речення і групує текст за природними межами. У такому випадку кожен чанк виглядає як більш завершений фрагмент думки.

Fixed-size chunking простіший, але він ріже текст за кількістю слів. Через це один чанк може починатися або закінчуватися посеред речення. Наприклад, у результатах fixed chunking видно фрагменти, які починаються з “method using...” або “to general lambda...”, тобто без повного початку думки.

У semantic chunking такі випадки трапляються рідше, тому ембеддинг краще представляє зміст чанка.

#### Чи є випадки розрізаних речень і як це впливає на ембеддинги?

Так, у fixed-size chunking є випадки розрізаних речень. Це нормально для простого підходу, бо він не аналізує структуру тексту, а просто бере певну кількість слів з overlap.

Такі розрізані речення можуть погіршувати якість ембеддингів. Якщо чанк починається з середини речення або закінчується до завершення думки, модель отримує неповний контекст. Через це вектор може гірше відображати реальний зміст фрагмента.

Semantic chunking зменшує цю проблему, бо розбиває текст по реченнях і намагається зберігати логічно завершені частини.

#### Як розмір overlap впливає на кількість чанків і покриття тексту?

Overlap збільшує перекриття між сусідніми чанками. Це корисно, бо інформація на межі двох чанків не втрачається. Якщо важливе речення або термін знаходиться біля кінця одного чанка, він може частково потрапити і в наступний чанк.

Але більший overlap збільшує кількість чанків. Наприклад, якщо chunk size = 120 слів, а overlap = 30, то наступний чанк починається не через 120 слів, а через 90 слів. Тому текст покривається щільніше, але створюється більше векторів і зростає обсяг даних у Pinecone.

Якщо overlap занадто малий, можна втратити контекст на межах чанків. Якщо overlap занадто великий, буде багато дублювання і зайві витрати на зберігання та пошук. У цьому завданні overlap = 30 для chunk size = 120 виглядає нормальним компромісом.

---

## Частина 5 — Гібридний пошук

Нижче наведено оновлений прогін `06_hybrid_search.py` після виправлення RRF-об'єднання за `arxiv_id`.
BM25 і vector search тепер коректно можуть визначати один і той самий документ як спільний результат.

<details>
<summary>Повний вивід <code>06_hybrid_search.py</code> (BM25, vector, hybrid RRF для трьох запитів)</summary>

```text
(.venv) PS C:\Github\goit_db\nosql_2> python .\scripts\06_hybrid_search.py
Loading dataset from data\arxiv_subset.parquet
Building BM25 index...
Loading model: allenai/specter2_base
No sentence-transformers model found with name allenai/specter2_base. Creating a newone with mean pooling.

================================================================================
Query: BERT fine-tuning

=== Top-5 BM25 ===

#1
BM25 score: 19.1485
Title: A New Measure of Fine Tuning
Category: hep-ph
Year: 2007
Abstract: The solution to fine tuning is one of the principal motivations for Beyondthe Standard Model (BSM) Studies. However constraints on new physics indicate that many of these BSM models are also fine tuned (although to a much lesser extent). To compare these BSM models it is essential that we have a re...

#2
BM25 score: 17.5338
Title: The NMSSM Solution to the Fine-Tuning Problem, Precision Electroweak   Constraints and the Largest LEP Higgs Event Excess
Category: hep-ph
Year: 2007
Abstract: We present an extended study of how the Next to Minimal   Supersymmetric Model easily avoids fine-tuning in electroweak symmetry breaking for a SM-like light Higgs with mass in the vicinity of $100\gev$, as beautifully consistent with precisionelectroweak data, while escaping LEP constraints due to...

#3
BM25 score: 16.7417
Title: Fine-Tuning in Brane-antibrane Inflation
Category: hep-th
Year: 2007
Abstract: I give a brief overview of brane-antibrane inflation, with emphasis on theproblems of tuning to get a flat potential in the KKLMMT framework, and recent work on the nature of superpotential corrections in that model....

#4
BM25 score: 13.4309
Title: Natural SUSY Dark Matter: A Window on the GUT Scale
Category: hep-ph
Year: 2007
Abstract: One of the key motivations for supersymmetry is that it provides a naturalcandidate for dark matter. For a long time the density of this candidate particle fell within cosmological bounds across much of the SUSY parameter space. However with the precision results of WMAP, it has become apparent tha...

#5
BM25 score: 12.4601
Title: Conformal dynamics in gauge theories via non-perturbative   renormalization group
Category: hep-ph
Year: 2007
Abstract: The dynamics at the IR fixed point realized in the $SU(N_c)$ gauge theories with massless Dirac fermions is studied by means of the non-perturbative renormalization group. The analysis includes the IR fixed points with non-trivial Yukawa couplings. The renormalization properties of the scalar field ...

=== Top-5 Vector search ===

#1
Vector score: 0.8645
Title: Misere quotients for impartial games: Supplementary material
Category: math.CO
Year: 2007.0
Abstract: We provide supplementary appendices to the paper Misere quotients for impartial games. These include detailed solutions to many of the octal games discussed inthe paper, and descriptions of the algorithms used to compute most of our solutions....

#2
Vector score: 0.8533
Title: Introduction to Phase Transitions in Random Optimization Problems
Category: cond-mat.stat-mech
Year: 2007.0
Abstract: Notes of the lectures delivered in Les Houches during the Summer School onComplex Systems (July 2006)....

#3
Vector score: 0.8500
Title: Abstract Convexity and Cone-Vexing Abstractions
Category: math.FA
Year: 2007.0
Abstract: This talk is a write-up on some origins of abstract convexity and afew vexing limitations on the range of abstraction in convexity....

#4
Vector score: 0.8481
Title: The Compositions of the Differential Operations and Gateaux Directional   Derivative
Category: math.CO
Year: 2007.0
Abstract: In this paper we determine the number of the meaningful compositions of higher order of the differential operations and Gateaux directional derivative....

#5
Vector score: 0.8473
Title: Experimental local realism tests without fair sampling assumption
Category: quant-ph
Year: 2007.0
Abstract: Following the theoretical suggestion of Ref. [1,2], we present experimental results addressed to test restricted families of local realistic models, but without relying on the fair sampling assumption....

=== Top-5 Hybrid search with RRF, k=60 ===

#1
RRF score: 0.0292
Title: A New Measure of Fine Tuning
Category: hep-ph
Year: 2007
Sources: bm25, vector
BM25 rank: 1
Vector rank: 18
Abstract: The solution to fine tuning is one of the principal motivations for Beyondthe Standard Model (BSM) Studies. However constraints on new physics indicate that many of these BSM models are also fine tuned (although to a much lesser extent). To compare these BSM models it is essential that we have a re...

#2
RRF score: 0.0265
Title: Fine-Tuning in Brane-antibrane Inflation
Category: hep-th
Year: 2007
Sources: bm25, vector
BM25 rank: 3
Vector rank: 34
Abstract: I give a brief overview of brane-antibrane inflation, with emphasis on theproblems of tuning to get a flat potential in the KKLMMT framework, and recent work on the nature of superpotential corrections in that model....

#3
RRF score: 0.0225
Title: On the choice of coarse variables for dynamics
Category: nlin.CD
Year: 2007
Sources: bm25, vector
BM25 rank: 38
Vector rank: 21
Abstract: Two ideas for the choice of an adequate set of coarse variables allowing approximate autonomous dynamics for practical applications are presented. The coarse variables are meant to represent averaged behavior of a fine-scale autonomous dynamics....

#4
RRF score: 0.0164
Title: Misere quotients for impartial games: Supplementary material
Category: math.CO
Year: 2007.0
Sources: vector
BM25 rank: None
Vector rank: 1
Abstract: We provide supplementary appendices to the paper Misere quotients for impartial games. These include detailed solutions to many of the octal games discussed inthe paper, and descriptions of the algorithms used to compute most of our solutions....

#5
RRF score: 0.0161
Title: The NMSSM Solution to the Fine-Tuning Problem, Precision Electroweak   Constraints and the Largest LEP Higgs Event Excess
Category: hep-ph
Year: 2007
Sources: bm25
BM25 rank: 2
Vector rank: None
Abstract: We present an extended study of how the Next to Minimal   Supersymmetric Model easily avoids fine-tuning in electroweak symmetry breaking for a SM-like light Higgs with mass in the vicinity of $100\gev$, as beautifully consistent with precisionelectroweak data, while escaping LEP constraints due to...

=== Top-5 comparison ===
BM25 top-5 ids: ['0704.3659', '0705.2241', '0705.2982', '0705.4387', '0706.0031']
Vector top-5 ids: ['0704.2536', '0705.0439', '0705.2404', '0705.2793', '0706.0249']
Hybrid top-5 ids: ['0704.1003', '0705.2241', '0705.2404', '0705.2982', '0705.4387']

Documents in hybrid top-5 that are not in BM25 or Vector top-5:
- 0704.1003

================================================================================
Query: Yann LeCun convolutional networks

=== Top-5 BM25 ===

#1
BM25 score: 13.5079
Title: On Punctured Pragmatic Space-Time Codes in Block Fading Channel
Category: cs.IT
Year: 2007
Abstract: This paper considers the use of punctured convolutional codes to obtain pragmatic space-time trellis codes over block-fading channel. We show that good performance can be achieved even when puncturation is adopted and that we can still employ the same Viterbi decoder of the convolutional mother code...

#2
BM25 score: 13.1797
Title: Trellis-Coded Quantization Based on Maximum-Hamming-Distance Binary   Codes
Category: cs.IT
Year: 2007
Abstract: Most design approaches for trellis-coded quantization take advantage of the duality of trellis-coded quantization with trellis-coded modulation, and use the same empirically-found convolutional codes to label the trellis branches. This letter presents an alternative approach that instead takes advan...

#3
BM25 score: 8.1042
Title: Response of degree-correlated scale-free networks to stimuli
Category: cond-mat.dis-nn
Year: 2007
Abstract: The response of degree-correlated scale-free attractor networks to stimuliis studied. We show that degree-correlated scale-free networks are robust to random stimuli as well as the uncorrelated scale-free networks, while assortative (disassortative) scale-free networks are more (less) sensitive to ...

#4
BM25 score: 7.9658
Title: Optimization in Gradient Networks
Category: cond-mat.stat-mech
Year: 2007
Abstract: Gradient networks can be used to model the dominant structure of complex networks. Previous works have focused on random gradient networks. Here we study gradient networks that minimize jamming on substrate networks with scale-free and Erd\H{o}s-R\'enyi structure. We introduce structural correlation...

#5
BM25 score: 7.7701
Title: Simulation of Robustness against Lesions of Cortical Networks
Category: q-bio.NC
Year: 2007
Abstract: Structure entails function and thus a structural description of the brain will help to understand its function and may provide insights into many properties ofbrain systems, from their robustness and recovery from damage, to their dynamics andeven their evolution. Advances in the analysis of compl...

=== Top-5 Vector search ===

#1
Vector score: 0.8479
Title: Multilayer Perceptron with Functional Inputs: an Inverse Regression   Approach
Category: math.ST
Year: 2007.0
Abstract: Functional data analysis is a growing research field as more and more practical applications involve functional data. In this paper, we focus on the problem ofregression and classification with functional predictors: the model suggested combines an efficient dimension reduction procedure [functiona...

#2
Vector score: 0.8431
Title: The Netsukuku network topology
Category: cs.NI
Year: 2007.0
Abstract: In this document, we describe the fractal structure of the Netsukuku topology. Moreover, we show how it is possible to use the QSPN v2 on the high levels of the fractal....

#3
Vector score: 0.8429
Title: The Compositions of the Differential Operations and Gateaux Directional   Derivative
Category: math.CO
Year: 2007.0
Abstract: In this paper we determine the number of the meaningful compositions of higher order of the differential operations and Gateaux directional derivative....

#4
Vector score: 0.8346
Title: Modeling the field of laser welding melt pool by RBFNN
Category: physics.comp-ph
Year: 2007.0
Abstract: Efficient control of a laser welding process requires the reliable prediction of process behavior. A statistical method of field modeling, based on normalized RBFNN, can be successfully used to predict the spatiotemporal dynamics of surface optical activity in the laser welding process. In this arti...

#5
Vector score: 0.8314
Title: Adaptive classification of temporal signals in fixed-weights recurrent   neural networks: an existence proof
Category: math.OC
Year: 2007.0
Abstract: We address the important theoretical question why a recurrent neural network with fixed weights can adaptively classify time-varied signals in the presence of additive noise and parametric perturbations. We provide a mathematical proof assumingthat unknown parameters are allowed to enter the signal...

=== Top-5 Hybrid search with RRF, k=60 ===

#1
RRF score: 0.0308
Title: Optimization in Gradient Networks
Category: cond-mat.stat-mech
Year: 2007
Sources: bm25, vector
BM25 rank: 4
Vector rank: 6
Abstract: Gradient networks can be used to model the dominant structure of complex networks. Previous works have focused on random gradient networks. Here we study gradient networks that minimize jamming on substrate networks with scale-free and Erd\H{o}s-R\'enyi structure. We introduce structural correlation...

#2
RRF score: 0.0257
Title: Simulation of Robustness against Lesions of Cortical Networks
Category: q-bio.NC
Year: 2007
Sources: bm25, vector
BM25 rank: 5
Vector rank: 37
Abstract: Structure entails function and thus a structural description of the brain will help to understand its function and may provide insights into many properties ofbrain systems, from their robustness and recovery from damage, to their dynamics andeven their evolution. Advances in the analysis of compl...

#3
RRF score: 0.0242
Title: DIA-MCIS. An Importance Sampling Network Randomizer for Network Motif   Discovery and Other Topological Observables in Transcription Networks
Category: q-bio.QM
Year: 2007
Sources: bm25, vector
BM25 rank: 22
Vector rank: 23
Abstract: Transcription networks, and other directed networks can be characterized by some topological observables such as for example subgraph occurrence (network motifs). In order to perform such kind of analysis, it is necessary to be able to generatesuitable randomized network ensembles. Typically, one c...

#4
RRF score: 0.0164
Title: On Punctured Pragmatic Space-Time Codes in Block Fading Channel
Category: cs.IT
Year: 2007
Sources: bm25
BM25 rank: 1
Vector rank: None
Abstract: This paper considers the use of punctured convolutional codes to obtain pragmatic space-time trellis codes over block-fading channel. We show that good performance can be achieved even when puncturation is adopted and that we can still employ the same Viterbi decoder of the convolutional mother code...

#5
RRF score: 0.0164
Title: Multilayer Perceptron with Functional Inputs: an Inverse Regression   Approach
Category: math.ST
Year: 2007.0
Sources: vector
BM25 rank: None
Vector rank: 1
Abstract: Functional data analysis is a growing research field as more and more practical applications involve functional data. In this paper, we focus on the problem ofregression and classification with functional predictors: the model suggested combines an efficient dimension reduction procedure [functiona...

=== Top-5 comparison ===
BM25 top-5 ids: ['0704.0282', '0704.0392', '0704.1144', '0704.1411', '0704.1849']
Vector top-5 ids: ['0704.0611', '0705.0211', '0705.0819', '0705.3370', '0706.0249']
Hybrid top-5 ids: ['0704.0282', '0704.0392', '0704.1144', '0705.0211', '0706.0118']

Documents in hybrid top-5 that are not in BM25 or Vector top-5:
- 0706.0118

================================================================================
Query: making computers understand human emotions from text

=== Top-5 BM25 ===

#1
BM25 score: 21.8804
Title: On the Development of Text Input Method - Lessons Learned
Category: cs.CL
Year: 2007
Abstract: Intelligent Input Methods (IM) are essential for making text entries in many East Asian scripts, but their application to other languages has not been fully explored. This paper discusses how such tools can contribute to the development of computer processing of other oriental languages. We propose ...

#2
BM25 score: 17.0865
Title: An Automated Evaluation Metric for Chinese Text Entry
Category: cs.HC
Year: 2007
Abstract: In this paper, we propose an automated evaluation metric for text entry. We also consider possible improvements to existing text entry evaluation metrics, suchas the minimum string distance error rate, keystrokes per character, cost per correction, and a unified approach proposed by MacKenzie, so t...

#3
BM25 score: 16.7227
Title: Towards Understanding the Origin of Genetic Languages
Category: q-bio.GN
Year: 2007
Abstract: Molecular biology is a nanotechnology that works--it has worked for billions of years and in an amazing variety of circumstances. At its core is a system for acquiring, processing and communicating information that is universal, from viruses and bacteria to human beings. Advances in genetics and exp...

#4
BM25 score: 12.1845
Title: Detecting anchoring in financial markets
Category: q-fin.TR
Year: 2007
Abstract: Anchoring is a term used in psychology to describe the common human tendency to rely too heavily (anchor) on one piece of information when making decisions. A trading algorithm inspired by biological motors, introduced by L. Gil\cite{Gil}, is suggested as a testing ground for anchoring in financial ...

#5
BM25 score: 11.8844
Title: Maximal C*-algebras of quotients and injective envelopes of C*-algebras
Category: math.OA
Year: 2007
Abstract: A new C*-enlargement of a C*-algebra $A$ nested between the local multiplier algebra $M_{\text{loc}}(A)$ of $A$ and its injective envelope $I(A)$ is introduced. Various aspects of this maximal C*-algebra of quotients, $Q_{\text{max}}(A)$, are studied, notably in the setting of AW*-algebras. As a by-...

=== Top-5 Vector search ===

#1
Vector score: 0.8287
Title: Opinion Dynamics and Sociophysics
Category: physics.soc-ph
Year: 2007.0
Abstract: No abstract given. Contents:   I. Definition and Introduction   II. Schelling Model   III. Opinion Dynamics   IV. Languages, Hierarchies and Football   V. Future Directions...

#2
Vector score: 0.8228
Title: On the Development of Text Input Method - Lessons Learned
Category: cs.CL
Year: 2007.0
Abstract: Intelligent Input Methods (IM) are essential for making text entries in many East Asian scripts, but their application to other languages has not been fully explored. This paper discusses how such tools can contribute to the development of computer processing of other oriental languages. We propose ...

#3
Vector score: 0.8092
Title: Extracting the hierarchical organization of complex systems
Category: physics.soc-ph
Year: 2007.0
Abstract: Extracting understanding from the growing ``sea'' of biological and socio-economic data is one of the most pressing scientific challenges facing us. Here, we introduce and validate an unsupervised method that is able to accurately extract the hierarchical organization of complex biological, social, ...

#4
Vector score: 0.8028
Title: Novelty and Collective Attention
Category: cs.CY
Year: 2007.0
Abstract: The subject of collective attention is central to an information age wheremillions of people are inundated with daily messages. It is thus of interest to understand how attention to novel items propagates and eventually fades among large populations. We have analyzed the dynamics of collective atte...

#5
Vector score: 0.8021
Title: Narratives within immersive technologies
Category: cs.HC
Year: 2007.0
Abstract: The main goal of this project is to research technical advances in order to enhance the possibility to develop narratives within immersive mediated environments. An important part of the research is concerned with the question of how a script can be written, annotated and realized for an immersive c...

=== Top-5 Hybrid search with RRF, k=60 ===

#1
RRF score: 0.0325
Title: On the Development of Text Input Method - Lessons Learned
Category: cs.CL
Year: 2007
Sources: bm25, vector
BM25 rank: 1
Vector rank: 2
Abstract: Intelligent Input Methods (IM) are essential for making text entries in many East Asian scripts, but their application to other languages has not been fully explored. This paper discusses how such tools can contribute to the development of computer processing of other oriental languages. We propose ...

#2
RRF score: 0.0293
Title: Detecting anchoring in financial markets
Category: q-fin.TR
Year: 2007
Sources: bm25, vector
BM25 rank: 4
Vector rank: 13
Abstract: Anchoring is a term used in psychology to describe the common human tendency to rely too heavily (anchor) on one piece of information when making decisions. A trading algorithm inspired by biological motors, introduced by L. Gil\cite{Gil}, is suggested as a testing ground for anchoring in financial ...

#3
RRF score: 0.0257
Title: The social aspects of quantum entanglement
Category: physics.pop-ph
Year: 2007
Sources: bm25, vector
BM25 rank: 25
Vector rank: 12
Abstract: This brief article discusses some aspects of quantum theory and their impact on popular culture. The basic features of quantum entanglement between two or moreparties are introduced in a language suitable for a general audience, and metaphorically connected to love and faithfulness in human relatio...

#4
RRF score: 0.0256
Title: An Automated Evaluation Metric for Chinese Text Entry
Category: cs.HC
Year: 2007
Sources: bm25, vector
BM25 rank: 2
Vector rank: 46
Abstract: In this paper, we propose an automated evaluation metric for text entry. We also consider possible improvements to existing text entry evaluation metrics, suchas the minimum string distance error rate, keystrokes per character, cost per correction, and a unified approach proposed by MacKenzie, so t...

#5
RRF score: 0.0246
Title: Information diffusion epidemics in social networks
Category: physics.soc-ph
Year: 2007
Sources: bm25, vector
BM25 rank: 13
Vector rank: 32
Abstract: The dynamics of information dissemination in social networks is of paramount importance in processes such as rumors or fads propagation, spread of product innovations or "word-of-mouth" communications. Due to the difficulty in tracking a specific information when it is transmitted by people, most un...

=== Top-5 comparison ===
BM25 top-5 ids: ['0704.3662', '0704.3665', '0704.3711', '0705.3319', '0705.3895']
Vector top-5 ids: ['0704.1158', '0704.2542', '0704.3665', '0705.0891', '0705.1679']
Hybrid top-5 ids: ['0704.3662', '0704.3665', '0705.3319', '0706.0286', '0706.0641']

Documents in hybrid top-5 that are not in BM25 or Vector top-5:
- 0706.0286
- 0706.0641
```

</details>

### Порівняльна таблиця методів пошуку з частини 5

| Запит | BM25 | Vector search | Hybrid RRF | Висновок |
|---|---|---|---|---|
| `BERT fine-tuning` | Добре реагує на точне слово `fine-tuning`, але через датасет 2007 року знаходить переважно фізичні статті про fine tuning. | Повертає семантично близькі, але не завжди тематично точні результати. | Піднімає документи, які мають позиції в обох списках, наприклад `A New Measure of Fine Tuning` має BM25 rank 1 і vector rank 18. | Hybrid краще показує компроміс між точним словом і семантичною близькістю. |
| `Yann LeCun convolutional networks` | Добре знаходить документи з точним словом `convolutional`, але частина результатів пов'язана з кодуванням або мережами не в сенсі CNN. | Знаходить документи про neural networks або perceptron, тобто ближче за змістом. | Піднімає документи, які одночасно мають непогані позиції в BM25 і vector search, наприклад `Optimization in Gradient Networks`. | Через обмеження датасету результати не ідеальні, але RRF демонструє змішування двох сигналів. |
| `making computers understand human emotions from text` | Добре знаходить текстові або мовні статті, наприклад `On the Development of Text Input Method`. | Краще ловить ширший зміст про соціальні процеси, емоції, увагу та текст. | Найкращий результат має BM25 rank 1 і vector rank 2, тобто документ підтриманий обома методами. | Для цього запиту hybrid виглядає найстабільніше. |

### Який метод дав кращий результат і чому?

У цьому експерименті hybrid search виглядає найбільш збалансованим методом, тому що він поєднує переваги BM25 і vector search.

BM25 добре реагує на точні слова із запиту. Наприклад, для `BERT fine-tuning` він знаходить статті зі словом `fine-tuning`, але через це частина результатів стосується не машинного навчання, а фізики та fine tuning у теоретичних моделях.

Vector search краще враховує семантичну близькість, але іноді повертає занадто загальні або неочевидні результати.

Hybrid search через RRF може підняти документи, які мають непогані позиції в обох списках. Тому він часто дає більш стабільну видачу, ніж кожен метод окремо.

### Чи є документи в top-5 hybrid, яких немає в top-5 окремих методів, і чому?

Так, у результатах є документи, які потрапили в top-5 hybrid search, але не були в top-5 окремо BM25 або vector search.

Наприклад, для запиту `BERT fine-tuning` документ `0704.1003` потрапив у top-5 hybrid, хоча його не було в top-5 BM25 і не було в top-5 vector search. Це сталося тому, що RRF враховує не тільки перші 5 документів, а ширший список кандидатів. Якщо документ має середні, але непогані позиції в обох методах, він може отримати вищий сумарний RRF score, ніж документ, який добре ранжується тільки одним методом.

Для запиту `Yann LeCun convolutional networks` аналогічно в hybrid top-5 з'явився документ `0706.0118`, якого не було в top-5 BM25 і vector search.

Для запиту `making computers understand human emotions from text` у hybrid top-5 з'явилися документи `0706.0286` і `0706.0641`, яких не було в top-5 окремих методів.

### Як зміна параметра k в RRF впливає на видачу?

Параметр `k` в RRF контролює, наскільки сильно враховується позиція документа в рейтингу.

При великому значенні, наприклад `k=60`, різниця між rank 1 і rank 10 згладжується. Це робить hybrid search більш стабільним: документ може піднятися вище, якщо він є в обох списках, навіть не на перших позиціях.

При малому значенні, наприклад `k=1`, перші позиції отримують набагато більшу вагу. У такому випадку top-1 або top-2 з BM25 чи vector search сильніше домінують у фінальній видачі.

Тобто `k=60` більше підходить для м'якого об'єднання двох методів, а `k=1` робить результат більш агресивно залежним від верхніх позицій окремих рейтингів.

### Примітка про підмножину даних

Оскільки скрипт `01_prepare_data.py` бере перші 10 000 валідних записів arXiv, у цьому запуску всі документи мають рік 2007. Через це приклад з фільтром `year >= 2021` не повертає результатів. Це не помилка пошуку, а наслідок вибраної підмножини даних.

---

## Частина 6 — Аналіз і висновки

### 1. Семантичний пошук vs BM25

Семантичний пошук краще працює, коли запит сформульований не точно такими словами, як у статті. Наприклад, запит object recognition in images може знаходити статті про computer vision, image classification або visual recognition, навіть якщо точна фраза не збігається.

BM25 краще працює, коли в запиті є конкретні ключові слова. Наприклад, для reinforcement learning він добре знаходить статті, де ця фраза прямо є в назві або abstract.

Загальне правило: semantic search краще для пошуку за змістом, BM25 — для точних термінів, назв методів і ключових фраз.

### 2. Вплив розміру чанка

Якщо чанк дуже маленький, наприклад 10–15 слів, він втрачає контекст. У ньому може бути потрібне слово, але незрозуміло, про що саме йдеться.

Якщо чанк дуже великий, наприклад 500+ слів, у ньому змішується багато різних думок. Через це ембеддинг стає менш точним для конкретного запиту.

Оптимальний розмір залежить від задачі. Для abstract достатньо приблизно 100–150 слів. Для довгих PDF або книг можна використовувати більші чанки з overlap.

### 3. Невідповідна метрика

Якщо використовувати euclidean для нормалізованих векторів, результати можуть бути схожими на cosine similarity, бо між ними є математичний зв’язок.

Для двох нормалізованих векторів:

```
||a - b||² = 2 - 2 · cosine(a, b)
```

Тобто чим більша cosine similarity, тим менша L2-відстань. Тому порядок результатів часто буде подібним.

Але краще все одно створювати індекс з тією метрикою, яка відповідає логіці моделі. У нашому випадку це cosine.

### 4. Обмеження Pinecone Starter

У безкоштовному тарифі Pinecone можна зіткнутися з обмеженнями на кількість індексів, обсяг збережених векторів, швидкість запису/читання і розмір metadata.

Якби датасет був не 10 000, а 10 мільйонів статей, я б не зберігав повні тексти в Pinecone. У Pinecone варто зберігати тільки вектори і короткі metadata: ID, title, category, year.
